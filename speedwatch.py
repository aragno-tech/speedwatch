import json
import subprocess
import sys
import datetime
import time

from lib.speedwatch_lib import (
    write_log, debug_log, send_email, create_influx_client,
    build_influx_payload, RECIPIENTS, DEVICE_HOST, DEVICE_ADDRESS
)
from lib.server_selector import get_server_candidates, record_server_used


def run_speedtest(server_id=None):
    server_arg = f" -s {server_id}" if server_id else ""
    # --accept-license and --accept-gdpr are required for non-interactive/headless use
    return subprocess.Popen(
        '/usr/bin/speedtest --accept-license --accept-gdpr -f json --progress=no' + server_arg,
        shell=True,
        stdout=subprocess.PIPE
    ).stdout.read().decode('utf-8')


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
    start_time = datetime.datetime.now()

    try:
        response = run_speedtest(server_id)
        if not response:
            write_log(f"(Speedtest error) Server not found: {server_label}")
            send_email(f"Speedtest error: {DEVICE_HOST}", f"Server not found: {server_label}", RECIPIENTS)
            return False
    except Exception as e:
        write_log(f"(Speedtest error) Exception for server {server_label}: {e}")
        send_email(f"Speedtest error: {DEVICE_HOST}", f"Exception for server {server_label}\n\n{str(e)}", RECIPIENTS)
        return False

    data = parse_speedtest_json(response)
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
    debug_log(f"InfluxDB client: {client}")
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
