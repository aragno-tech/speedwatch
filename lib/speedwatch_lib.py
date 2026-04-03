import smtplib
from email.mime.text import MIMEText
import socket
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from influxdb import InfluxDBClient
import urllib3

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_URL = os.getenv("INFLUXDB_URL")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
STORAGE = os.getenv("STORAGE", "influxdb")
# EMAIL_RECIPIENTS is expected as a comma-separated string in .env
RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'log', 'speed.log')
DEVICE_HOST = os.getenv("DEVICE_HOST") or socket.gethostname()
DEVICE_ADDRESS = os.getenv("DEVICE_ADDRESS")
LOG = os.getenv("LOG", "true").lower() == "true"
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(1 * 1024 * 1024)))  # default 1MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "3"))
SERVER_SKIP_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'log', 'server_skip.log')


def _make_rotating_logger(name, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handler = RotatingFileHandler(path, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    return logger


_logger = None
_skip_logger = None


def _get_logger():
    global _logger
    if _logger is None:
        _logger = _make_rotating_logger('speedwatch', LOG_PATH)
    return _logger


def _get_skip_logger():
    global _skip_logger
    if _skip_logger is None:
        _skip_logger = _make_rotating_logger('speedwatch.skip', SERVER_SKIP_LOG_PATH)
    return _skip_logger
SERVER_COUNT = int(os.getenv("SERVER_COUNT", "5"))
MONITOR_SERVER_IDS = [s.strip() for s in os.getenv("MONITOR_SERVER_IDS", "").split(",") if s.strip()]
THROTTLE_BLOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'throttle_block')
THROTTLE_COOLDOWN = 3600  # seconds


def is_throttle_blocked():
    if not os.path.isfile(THROTTLE_BLOCK_PATH):
        return False
    with open(THROTTLE_BLOCK_PATH, 'r') as f:
        blocked_at = float(f.read().strip())
    return (time.time() - blocked_at) < THROTTLE_COOLDOWN


def set_throttle_block():
    with open(THROTTLE_BLOCK_PATH, 'w') as f:
        f.write(str(time.time()))


def build_influx_payload(measurement, tags, fields):
    return [{"measurement": measurement, "tags": tags, "fields": fields}]


def write_log(text):
    if LOG:
        _get_logger().info(text.rstrip())


def write_server_log(text):
    if LOG:
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        _get_skip_logger().info(f"[{ts}] {text.rstrip()}")


def debug_log(text):
    if DEBUG:
        print(text)


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


def write_result(tags, fields):
    """Write one speed result to the active storage backend (STORAGE env var)."""
    if STORAGE in ("sqlite", "both"):
        import lib.storage_sqlite as _sq
        _sq.write_record(tags, fields)
    if STORAGE in ("influxdb", "both"):
        payload = build_influx_payload("Ookla", tags, fields)
        create_influx_client().write_points(payload)


def create_influx_client():
    urllib3.disable_warnings()
    return InfluxDBClient(
        host=INFLUXDB_URL,
        port=443,
        ssl=True,
        database=INFLUXDB_BUCKET,
        username='',  # InfluxDB v1 compatibility: token is passed as password
        password=INFLUXDB_TOKEN,
        headers={'Content-Type': 'text/plain; charset=utf-8'}
    )
