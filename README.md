# speedwatch

Automated internet speed monitoring for Raspberry Pi (or any Linux box).
Runs `speedtest` on a cron schedule, rotates between preferred Ookla servers,
and stores results in your choice of backend.

---

## Choose your setup

| | Multi-location (InfluxDB) | Single-home (SQLite) |
|---|---|---|
| Storage | InfluxDB Cloud (free tier) | Local file (`var/speeds.db`) |
| Dashboard | Grafana Cloud | Built-in (`dashboard.py`) |
| Requires cloud accounts | Yes | No |
| Best for | Multiple Pi devices, shared dashboards | Single device, no cloud |

---

## Setup: Single-home (SQLite)

### 1. Clone and install

```bash
git clone <repo-url> speedwatch
cd speedwatch
pip3 install -r requirements.txt
```

### 2. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` — the minimum required keys for SQLite mode:

```
STORAGE=sqlite
DEVICE_HOST=my-pi          # label shown in dashboard
DEVICE_ADDRESS=home        # location label
EMAIL_SENDER=              # optional — leave blank to disable email alerts
EMAIL_PASSWORD=
EMAIL_RECIPIENTS=
MONITOR_SERVER_IDS=8018,12919,31861   # comma-separated Ookla server IDs
```

Leave all `INFLUXDB_*` keys blank — they are not used in SQLite mode.

### 3. Run a test

```bash
python3 speedwatch.py --test-write   # verify DB write works
python3 speedwatch.py                # run one speed test
```

Results are written to `var/speeds.db`.

### 4. View the dashboard

```bash
python3 dashboard.py
```

Open `http://localhost:8080` in a browser.
To run on startup, add to crontab: `@reboot cd /path/to/speedwatch && python3 dashboard.py &`

### 5. Schedule speed tests

```bash
crontab -e
```

Add (runs every 30 minutes):
```
*/30 * * * * cd /path/to/speedwatch && python3 speedwatch.py >> log/cron.log 2>&1
```

---

## Setup: Multi-location (InfluxDB + Grafana)

### 1. Clone and install

```bash
git clone <repo-url> speedwatch
cd speedwatch
pip3 install -r requirements.txt
```

### 2. Create free cloud accounts

- **InfluxDB Cloud** — create a free account, create a bucket named `speedwatch`,
  generate an all-access API token (scoped tokens do not work with the v1 compat API).
- **Grafana Cloud** — create a free account.

### 3. Configure `.env`

```bash
cp .env.example .env
```

Edit `.env`:

```
STORAGE=influxdb
INFLUXDB_URL=<your-influxdb-host>        # host only, no https://
INFLUXDB_TOKEN=<all-access-token>
INFLUXDB_BUCKET=speedwatch
DEVICE_HOST=pi-home
DEVICE_ADDRESS=home
EMAIL_SENDER=you@gmail.com
EMAIL_PASSWORD=<app-password>
EMAIL_RECIPIENTS=you@gmail.com
MONITOR_SERVER_IDS=8018,12919,31861
```

### 4. Verify InfluxDB connection

```bash
python3 speedwatch.py --test-write
# Expected: influxdb write OK
```

### 5. Connect Grafana to InfluxDB

In Grafana: **Connections → Data Sources → Add → InfluxDB**

| Field | Value |
|---|---|
| Query language | InfluxQL |
| URL | `https://<your-influxdb-host>` |
| Database | `speedwatch` |
| User | your InfluxDB bucket ID |
| Password | your all-access token |

> Note: use bucket ID (not name) as the Grafana username. Find it in InfluxDB under **Buckets**.

### 6. Schedule speed tests

```bash
crontab -e
```

Add (runs every 30 minutes):
```
*/30 * * * * cd /path/to/speedwatch && python3 speedwatch.py >> log/cron.log 2>&1
```

---

## Finding Ookla server IDs

```bash
speedtest -L
```

Pick stable servers geographically close to you. Set them in `MONITOR_SERVER_IDS`.

---

## Other monitors

| Script | What it does |
|---|---|
| `lib/pingtest.py` | Periodic ping tests to configured hosts |
| `lib/notify_ip_change.py` | Emails you when your public IP changes |
