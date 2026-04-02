import json
import subprocess
import sys
import datetime
import time

from lib.speedwatch_lib import (
    write_log, debug_log, send_email, create_influx_client,
    build_influx_payload, RECIPIENTS, DEVICE_HOST, DEVICE_ADDRESS,
    is_throttle_blocked, set_throttle_block
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
        debug_log("Throttle block active, skipping")
        return False

    start_time = datetime.datetime.now()

    try:
        stdout, stderr = run_speedtest(server_id)
        if "Limit reached" in stderr or "Limit reached" in stdout:
            set_throttle_block()
            write_log(f"(Throttle) Ookla rate limit hit — blocking CLI for 1 hour")
            send_email(f"Speedtest throttled: {DEVICE_HOST}", "Ookla rate limit hit. CLI blocked for 1 hour.", RECIPIENTS)
            return False
        if not stdout:
            write_log(f"(Speedtest error) Server not found: {server_label}")
            send_email(f"Speedtest error: {DEVICE_HOST}", f"Server not found: {server_label}\n\n{stderr}", RECIPIENTS)
            return False
    except Exception as e:
        write_log(f"(Speedtest error) Exception for server {server_label}: {e}")
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
    payload = build_influx_payload("Ookla", tags, fields)
    debug_log(f"Payload: {payload}")

    client = create_influx_client()
    client.write_points(payload)

    end_time = datetime.datetime.now()
    write_log(
        f"{start_time.strftime('%H:%M:%S')} - {server_label} - {data['server']} - {data['download']} - {end_time.strftime('%H:%M:%S')}"
    )
    return True


if __name__ == "__main__":
    args = sys.argv[1:]
    if '-v' in args or '--verbose' in args:
        import lib.speedwatch_lib as _swlib
        _swlib.DEBUG = True
        args = [a for a in args if a not in ('-v', '--verbose')]
    if '--test-write' in args:
        payload = build_influx_payload(
            'Ookla',
            {'host': DEVICE_HOST, 'address': DEVICE_ADDRESS, 'server': 'test'},
            {'download': 1.0, 'upload': 1.0, 'ping': 1.0, 'jitter': 1.0, 'ploss': 0.0}
        )
        create_influx_client().write_points(payload)
        print('InfluxDB write OK')
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
            for fallback in fallbacks:
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
