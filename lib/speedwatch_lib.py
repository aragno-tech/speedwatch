import smtplib
from email.mime.text import MIMEText
import socket
import os
import os.path
from dotenv import load_dotenv
from influxdb import InfluxDBClient
import urllib3

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_DB = os.getenv("INFLUXDB_DB")

RECIPIENTS = ["recipient@example.com"]


def write_file(text, filepath):
    with open(filepath, 'a') as f:
        f.write(text)


def write_log(text):
    write_file(text.rstrip() + "\n", "/home/netmon/log/speed.log")


def send_email(subject, body, recipients, sender=EMAIL_SENDER, password=EMAIL_PASSWORD):
    hostname = socket.gethostname()
    body = body + "\n\nFrom: " + hostname
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
        smtp_server.login(sender, password)
        smtp_server.sendmail(sender, recipients, msg.as_string())
    print("Message sent!")


def create_influx_client():
    urllib3.disable_warnings()
    return InfluxDBClient(
        host=INFLUXDB_URL,
        port=443,
        ssl=True,
        database=INFLUXDB_DB,
        username='',
        password=INFLUXDB_TOKEN,
        headers={'Content-Type': 'text/plain; charset=utf-8'}
    )
