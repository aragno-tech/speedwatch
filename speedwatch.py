import re
import subprocess
import sys
import datetime
import time

from lib.speedwatch_lib import (
    write_log, send_email, create_influx_client,
    build_influx_payload, RECIPIENTS, DEVICE_HOST, DEVICE_ADDRESS
)


def run_speedtest(server_id=None):
    server_arg = f" -s {server_id}" if server_id else ""
    return subprocess.Popen(
        '/usr/bin/speedtest --accept-license --accept-gdpr' + server_arg,
        shell=True,
        stdout=subprocess.PIPE
    ).stdout.read().decode('utf-8')


def parse_speedtest_output(response):
    server = re.search(r'Server:\s+(.*?)\n', response, re.MULTILINE)
    ping = re.search(r'Latency:\s+(.*?)\s', response, re.MULTILINE)
    download = re.search(r'Download:\s+(.*?)\s', response, re.MULTILINE)
    upload = re.search(r'Upload:\s+(.*?)\s', response, re.MULTILINE)
    jitter = re.search(r'Latency:.*?jitter:\s+(.*?)ms', response, re.MULTILINE)
    ploss = re.search(r'Loss:\s+(.*?)%\s', response, re.MULTILINE)
    return {
        'server': server.group(1),
        'ping': ping.group(1),
        'download': download.group(1),
        'upload': upload.group(1),
        'jitter': jitter.group(1),
        'ploss': ploss.group(1) if ploss else '0.0'
    }


def run_test_for_server(server_id=None):
    server_label = server_id if server_id else "closest"
    start_time = datetime.datetime.now()

    try:
        response = run_speedtest(server_id)
        if not response:
            write_log(f"(Speedtest error) Server not found: {server_label}")
            send_email(f"Speedtest error: {DEVICE_HOST}", f"Server not found: {server_label}", RECIPIENTS)
            return
    except Exception as e:
        write_log(f"(Speedtest error) Exception for server {server_label}: {e}")
        send_email(f"Speedtest error: {DEVICE_HOST}", f"Exception for server {server_label}\n\n{str(e)}", RECIPIENTS)
        return

    data = parse_speedtest_output(response)
    tags = {"host": DEVICE_HOST, "address": DEVICE_ADDRESS, "server": data['server']}
    fields = {
        "download": float(data['download']),
        "upload": float(data['upload']),
        "ping": float(data['ping']),
        "jitter": float(data['jitter']),
        "ploss": float(data['ploss'])
    }
    payload = build_influx_payload("Ookla", tags, fields)

    client = create_influx_client()
    client.write_points(payload)

    end_time = datetime.datetime.now()
    write_log(
        f"{start_time.strftime('%H:%M:%S')} - {server_label} - {data['server']} - {data['download']} - {end_time.strftime('%H:%M:%S')}"
    )


if __name__ == "__main__":
    server_ids = sys.argv[1:]
    script_start_time = datetime.datetime.now()
    write_log(f"--START-- {script_start_time.strftime('%H:%M:%S')} --START--")

    if server_ids:
        for i, server_id in enumerate(server_ids):
            run_test_for_server(server_id)
            if i < len(server_ids) - 1:
                time.sleep(90)
    else:
        run_test_for_server()

    script_end_time = datetime.datetime.now()
    write_log(f"--END-- {script_start_time.strftime('%H:%M:%S')}->{script_end_time.strftime('%H:%M:%S')} --END--")
