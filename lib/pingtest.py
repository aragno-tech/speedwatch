import re
import subprocess
#import connect
import sys
import os
from dotenv import load_dotenv
from influxdb import InfluxDBClient
import urllib3

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_DB = os.getenv("INFLUXDB_DB")

# fjerne advarsel om at SSL sertifikat ikke er verifisert.
urllib3.disable_warnings()

args = sys.argv
#url = arguments[1]

args.pop(0)

for url in args:
    #Start of for loop
    #print(url)

    response = subprocess.Popen('/usr/bin/ping -c5 ' + url, shell=True, stdout=subprocess.PIPE).stdout.read().decode('utf-8')

    ploss = re.search('received,\s+(.*?)%', response, re.MULTILINE)
    ping = re.search('mdev =\s(.*?)/(.*?)/(.*?)/(.*?)\s', response, re.MULTILINE)

    ploss = ploss.group(1)
    min = ping.group(1)
    avg = ping.group(2)
    max = ping.group(3)
    mdev = ping.group(4)

    speed_data = [
        {
            "measurement" : "ping",
            "tags" : {
                "host": "raspNetMon",
                "address": "MB81",
                "url": '' + url
            },
            "fields" : {
                "min": float(min),
                "avg": float(avg),
                "max": float(max),
                "ploss": float(ploss),
                "jitter": float(mdev)
            }
        }
    ]

    #print(url, float(avg))

    client = InfluxDBClient(
            host=INFLUXDB_URL,
            port=443,
            ssl=True,
            database=INFLUXDB_DB,
            username='',
            password=INFLUXDB_TOKEN,
            headers={'Content-Type': 'text/plain; charset=utf-8'}
            )

    client.write_points(speed_data)
    #end of for loop
#print("done")
