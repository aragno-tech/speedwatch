import json
import subprocess
import sys
import datetime
import time

from lib.speedwatch_lib import (
    write_log, write_server_log, debug_log, send_email, write_result,
    RECIPIENTS, DEVICE_HOST, DEVICE_ADDRESS,
    is_throttle_blocked, set_throttle_block, STORAGE,
    INFLUXDB_TOKEN, INFLUXDB_URL, INFLUXDB_BUCKET
)
from lib.server_selector import get_server_candidates, record_server_used


def run_speedtest(server_id=None):
    server_arg = f" -s {server_id}" if server_id else ""
    # --accept-license and --accept-gdpr are required for non-interactive/headless use
    proc = subprocess.Popen(
        '/usr/bin/speedtest --accept-license --accept-gdpr -f json --progress=no' + server_arg,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = proc.communicate()
    return stdout.decode('utf-8'), stderr.decode('utf-8')


def parse_speedtest_json(response):
    data = json.loads(response)
    srv = data['server']
    return {
        'server':   f"{srv['name']} - {srv['location']} (id: {srv['id']})",
        'ping':     data['ping']['latency'],
        'jitter':   data['ping']['jitter'],
        'download': data['download']['bandwidth'] * 8 / 1_000_000,
        'upload':   data['upload']['bandwidth'] * 8 / 1_000_000,
        'ploss':    data.get('packetLoss', 0.0),
    }


def run_test_for_server(server_id=None):
    """Run a speedtest against the given server. Returns True on success, False on failure."""
    server_label = server_id if server_id else "closest"

    if is_throttle_blocked():
        write_log(f"(Throttle block) Skipping speedtest — cooling down for 1 hour")
        write_server_log(f"SKIP server={server_label} reason=throttle_block")
        debug_log("Throttle block active, skipping")
        return False

    start_time = datetime.datetime.now()

    try:
        stdout, stderr = run_speedtest(server_id)
        if "Limit reached" in stderr or "Limit reached" in stdout:
            set_throttle_block()
            write_log(f"(Throttle) Ookla rate limit hit — blocking CLI for 1 hour")
            write_server_log(f"SKIP server={server_label} reason=rate_limit stderr={stderr.strip()!r}")
            send_email(f"Speedtest throttled: {DEVICE_HOST}", "Ookla rate limit hit. CLI blocked for 1 hour.", RECIPIENTS)
            return False
        if not stdout:
            write_log(f"(Speedtest error) Server not found: {server_label}")
            write_server_log(f"SKIP server={server_label} reason=no_output stderr={stderr.strip()!r}")
            send_email(f"Speedtest error: {DEVICE_HOST}", f"Server not found: {server_label}\n\n{stderr}", RECIPIENTS)
            return False
    except Exception as e:
        write_log(f"(Speedtest error) Exception for server {server_label}: {e}")
        write_server_log(f"SKIP server={server_label} reason=exception error={str(e)!r} stderr={stderr.strip()!r}")
        send_email(f"Speedtest error: {DEVICE_HOST}", f"Exception for server {server_label}\n\n{str(e)}\n\n{stderr}", RECIPIENTS)
        return False

    data = parse_speedtest_json(stdout)
    tags = {"host": DEVICE_HOST, "address": DEVICE_ADDRESS, "server": data['server']}
    fields = {
        "download": float(data['download']),
        "upload": float(data['upload']),
        "ping": float(data['ping']),
        "jitter": float(data['jitter']),
        "ploss": float(data['ploss'])
    }
    debug_log(f"Writing result via {STORAGE}: {tags} {fields}")
    write_result(tags, fields)

    end_time = datetime.datetime.now()
    write_log(
        f"{start_time.strftime('%H:%M:%S')} - {server_label} - {data['server']} - {data['download']} - {end_time.strftime('%H:%M:%S')}"
    )
    return True


if __name__ == "__main__":
    args = sys.argv[1:]

    # Parse --storage=<backend> override
    import lib.speedwatch_lib as _swlib
    storage_override = None
    for arg in args:
        if arg.startswith('--storage='):
            storage_override = arg.split('=', 1)[1]
            args = [a for a in args if a != arg]
            break
    if storage_override:
        if storage_override not in ('influxdb', 'sqlite', 'both'):
            print(f"Error: invalid --storage value '{storage_override}'. Must be influxdb, sqlite, or both.")
            sys.exit(1)
        _swlib.STORAGE = storage_override

    # Re-read STORAGE after any override
    active_storage = _swlib.STORAGE

    if '-h' in args or '--help' in args:
        print(
            "Usage: python3 speedwatch.py [OPTIONS] [SERVER_ID ...]\n"
            "\n"
            "  No arguments    Rotate through MONITOR_SERVER_IDS if set; otherwise auto-select from speedtest -L\n"
            "  SERVER_ID ...   Run against specific Ookla server ID(s), e.g. 8018 12919\n"
            "\n"
            "Options:\n"
            "  -h, --help              Show this help message and exit\n"
            "  -v, --verbose           Print debug output to stdout\n"
            "  --storage=<backend>     Override storage backend for this run: influxdb, sqlite, or both\n"
            "  --test-write            Write a dummy result to the active storage backend and exit\n"
            "\n"
            f"Active storage backend: {active_storage}  (set STORAGE= in .env or use --storage=)\n"
            "Find server IDs with: speedtest -L"
        )
        sys.exit(0)

    # Validate InfluxDB config before any write attempt
    if active_storage in ('influxdb', 'both'):
        missing = [k for k, v in [
            ('INFLUXDB_URL', INFLUXDB_URL),
            ('INFLUXDB_TOKEN', INFLUXDB_TOKEN),
            ('INFLUXDB_BUCKET', INFLUXDB_BUCKET),
        ] if not v]
        if missing:
            print(f"Error: InfluxDB backend requires these .env keys to be set: {', '.join(missing)}")
            sys.exit(1)

    if '-v' in args or '--verbose' in args:
        _swlib.DEBUG = True
        args = [a for a in args if a not in ('-v', '--verbose')]
    test_write = '--test-write' in args
    args = [a for a in args if a != '--test-write']

    # Anything remaining must be a numeric server ID
    invalid = [a for a in args if not a.isdigit()]
    if invalid:
        print(f"Error: unrecognised argument(s): {', '.join(invalid)}")
        print("Server IDs must be integers. Run with -h for usage.")
        sys.exit(1)

    if test_write:
        write_result(
            {'host': DEVICE_HOST, 'address': DEVICE_ADDRESS, 'server': 'test'},
            {'download': 1.0, 'upload': 1.0, 'ping': 1.0, 'jitter': 1.0, 'ploss': 0.0}
        )
        print(f'{active_storage} write OK')
        sys.exit(0)
    server_ids = args
    script_start_time = datetime.datetime.now()
    write_log(f"--START-- {script_start_time.strftime('%H:%M:%S')} --START--")

    if server_ids:
        # Manual override: server IDs supplied as arguments (useful for testing)
        for i, server_id in enumerate(server_ids):
            run_test_for_server(server_id)
            # Sleep between servers to avoid hitting the Ookla throttle limit
            if i < len(server_ids) - 1:
                time.sleep(90)
    else:
        # Normal cron invocation: auto-select next preferred server, fall back if it fails
        preferred, fallbacks = get_server_candidates()

        if run_test_for_server(preferred['id']):
            record_server_used(preferred['id'], preferred['name'])
        else:
            succeeded = False
            if is_throttle_blocked():
                write_server_log(f"SKIP fallbacks — throttle block active, not attempting {len(fallbacks)} fallback(s)")
            else:
                for fallback in fallbacks:
                    write_server_log(f"FALLBACK preferred={preferred['id']} ({preferred['name']}) trying_fallback={fallback['id']} ({fallback['name']})")
                    if run_test_for_server(fallback['id']):
                        # Advance rotation past the failed preferred server
                        record_server_used(preferred['id'], preferred['name'])
                        succeeded = True
                        break
            if not succeeded:
                write_log("(Error) All servers failed — preferred and all fallbacks")
                send_email(f"Speedtest error: {DEVICE_HOST}", "All servers failed — preferred and all fallbacks", RECIPIENTS)

    script_end_time = datetime.datetime.now()
    write_log(f"--END-- {script_start_time.strftime('%H:%M:%S')}->{script_end_time.strftime('%H:%M:%S')} --END--")
