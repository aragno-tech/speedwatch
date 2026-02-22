import re
import subprocess
import sys
import os
import urllib3

from speedwatch_lib import create_influx_client

PING_HOST = os.getenv("PING_HOST")
PING_ADDRESS = os.getenv("PING_ADDRESS")


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


def build_ping_payload(url, data):
    return [
        {
            "measurement": "ping",
            "tags": {
                "host": PING_HOST,
                "address": PING_ADDRESS,
                "url": url
            },
            "fields": {
                "min": float(data['ping_min']),
                "avg": float(data['ping_avg']),
                "max": float(data['ping_max']),
                "ploss": float(data['packet_loss']),
                "jitter": float(data['ping_mdev'])
            }
        }
    ]


if __name__ == "__main__":
    urllib3.disable_warnings()
    urls = sys.argv[1:]
    for url in urls:
        response = run_ping(url)
        data = parse_ping_output(response)
        payload = build_ping_payload(url, data)
        client = create_influx_client()
        client.write_points(payload)
