import sqlite3
import os
import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'speeds.db')
SQLITE_MAX_ROWS = int(os.getenv("SQLITE_MAX_ROWS", "10000"))

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS speeds (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    host      TEXT,
    address   TEXT,
    server    TEXT,
    download  REAL,
    upload    REAL,
    ping      REAL,
    jitter    REAL,
    ploss     REAL
)
"""


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(_CREATE_TABLE)
    conn.commit()
    return conn


def write_record(tags, fields):
    """Insert one speed result row. tags: {host, address, server}. fields: {download, upload, ping, jitter, ploss}."""
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    with _connect() as conn:
        conn.execute(
            "INSERT INTO speeds (timestamp, host, address, server, download, upload, ping, jitter, ploss) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                ts,
                tags.get('host'),
                tags.get('address'),
                tags.get('server'),
                fields.get('download'),
                fields.get('upload'),
                fields.get('ping'),
                fields.get('jitter'),
                fields.get('ploss'),
            )
        )
        # Trim oldest rows if over the limit
        conn.execute(
            "DELETE FROM speeds WHERE id IN ("
            "  SELECT id FROM speeds ORDER BY id ASC LIMIT MAX(0, (SELECT COUNT(*) FROM speeds) - ?)"
            ")",
            (SQLITE_MAX_ROWS,)
        )


def read_records(limit=500):
    """Return up to `limit` rows as a list of dicts, newest first."""
    if not os.path.isfile(DB_PATH):
        return []
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT timestamp, host, address, server, download, upload, ping, jitter, ploss "
            "FROM speeds ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]
