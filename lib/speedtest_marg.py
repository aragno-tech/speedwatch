import re
import subprocess
from influxdb import InfluxDBClient
import urllib3
import sys
import datetime
import socket
import time
import os
from dotenv import load_dotenv
from speedtest_lib import *

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_DB = os.getenv("INFLUXDB_DB")

testhost = socket.gethostname()
testaddress = "MB208"
dolog = 1


# fjerne advarsel om at SSL sertifikat ikke er verifisert.
urllib3.disable_warnings()

# lag database i bucket paa influxdb
#curl --request POST https://eu-central-1-1.aws.cloud2.influxdata.com/api/v2/dbrps \
#  --header "Authorization: Token INFLUXDB_TOKEN" \
#  --header 'Content-type: application/json' \
#  --data '{
#        "bucketID": "INFLUXDB_BUCKET",
#        "database": "INFLUXDB_DB",
#        "default": true,
#        "orgID": "INFLUXDB_ORG",
#        "retention_policy": "standard"
#      }'

serverstring = ""

if len(sys.argv) > 1 :
  args = sys.argv
  args.pop(0)
  if dolog:
   scriptstarttime = datetime.datetime.now()
   writelog("--START-- " + scriptstarttime.strftime("%H:%M:%S") + " --START--")
  for serverurl in args:
    #start foor loop
    if dolog:
      starttime = datetime.datetime.now()
    serverstring = " -s " + serverurl

    try:
      response = subprocess.Popen('/usr/bin/speedtest --accept-license --accept-gdpr' + serverstring, shell=True, stdout=subprocess.PIPE).stdout.read().decode('utf-8')
      if len(response) == 0: 
          writelog("(Speedtest error (if)) The speedtest serverid does not exist: " + serverurl)
          send_email("Speedtest error(if): " + testhost, "The speedtest serverid does not exist: " + serverurl, recipients)
          #print ("To: recipient@example.com\nSubject:raspNetMon (Speedtest error)\n\nThe speedtest serverid does not exist: " + serverurl + "\n")    
          continue
    except Exception as e:
      writelog("(Speedtest error (except)) The speedtest serverid does not exist: " + serverurl)
      send_email("Speedtest error (except): " + testhost, "The speedtest serverid does not exist: " + serverurl + "\n\n" + e, recipients)
      print(e)
      print ("Err: The speedtest serverid does not exist: " + serverurl + "\n")
      continue

    server = re.search('Server:\s+(.*?)\n', response, re.MULTILINE)
    ping = re.search('Latency:\s+(.*?)\s', response, re.MULTILINE)
    download = re.search('Download:\s+(.*?)\s', response, re.MULTILINE)
    upload = re.search('Upload:\s+(.*?)\s', response, re.MULTILINE)
    jitter = re.search('Latency:.*?jitter:\s+(.*?)ms', response, re.MULTILINE)
    ploss = re.search('Loss:\s+(.*?)%\s', response, re.MULTILINE)

    server = server.group(1)
    ping = ping.group(1)
    download = download.group(1)
    upload = upload.group(1)
    jitter = jitter.group(1)
    if ploss:
      ploss = ploss.group(1)
    else:
      ploss = 0.0

    speed_data = [
      {
        "measurement" : "Ookla",
        "tags" : {
          "host": testhost,
          "address": testaddress,
          "server": server
        },
        "fields" : {
          "download": float(download),
          "upload": float(upload),
          "ping": float(ping),
          "jitter": float(jitter),
          "ploss": float(ploss)
        }
      }
    ]

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
    if dolog:
      endtime = datetime.datetime.now()
      writelog(starttime.strftime("%H:%M:%S") + " - " + serverurl + " - " + server + " - " + download + " - " + endtime.strftime("%H:%M:%S"))
    # sleep for x seconds
    time.sleep(90)
    #end for loop
  if dolog:
    scriptendtime = datetime.datetime.now()
    writelog("--END-- " + scriptstarttime.strftime("%H:%M:%S") + "->" +  scriptendtime.strftime("%H:%M:%S") + " --END--")

else:
  print("needs at least one server url")
