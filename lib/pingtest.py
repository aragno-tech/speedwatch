import re
import subprocess
import sys
import urllib3

from speedwatch_lib import create_influx_client, build_influx_payload, DEVICE_HOST, DEVICE_ADDRESS


def run_ping(url):
    return subprocess.Popen(
        '/usr/bin/ping -c5 ' + url,
        shell=True,
        stdout=subprocess.PIPE
    ).stdout.read().decode('utf-8')


def parse_ping_output(response):
    packet_loss = re.search(r'received,\s+(.*?)%', response, re.MULTILINE)
    ping_stats = re.search(r'mdev =\s(.*?)/(.*?)/(.*?)/(.*?)\s', response, re.MULTILINE)
    return {
        'packet_loss': packet_loss.group(1),
        'ping_min': ping_stats.group(1),
        'ping_avg': ping_stats.group(2),
        'ping_max': ping_stats.group(3),
        'ping_mdev': ping_stats.group(4)
    }


if __name__ == "__main__":
    urllib3.disable_warnings()
    urls = sys.argv[1:]
    for url in urls:
        response = run_ping(url)
        data = parse_ping_output(response)
        tags = {"host": DEVICE_HOST, "address": DEVICE_ADDRESS, "url": url}
        fields = {
            "min": float(data['ping_min']),
            "avg": float(data['ping_avg']),
            "max": float(data['ping_max']),
            "ploss": float(data['packet_loss']),
            "jitter": float(data['ping_mdev'])
        }
        payload = build_influx_payload("ping", tags, fields)
        client = create_influx_client()
        client.write_points(payload)
