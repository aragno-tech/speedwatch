# Speedwatch: Setup Guide

This guide covers both setup modes. Start with whichever fits your situation.

- **Single-home (SQLite)** — one device, no cloud accounts, local dashboard
- **Multi-location (InfluxDB + Grafana)** — multiple devices, shared cloud dashboard

---

## Single-home setup (SQLite)

### 1. Install the speedtest CLI

The Ookla speedtest CLI must be installed before running setup:

```bash
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt install speedtest
```

Verify it works:

```bash
speedtest --version
```

### 2. Download speedwatch and run setup

```bash
git clone https://github.com/aragno-tech/speedwatch
cd speedwatch
bash setup.sh
```

The script will:
- Install Python dependencies
- Ask for a device name, location label, and Ookla server IDs
- Write your `.env` file
- Verify the database works
- Optionally add cron entries for automatic tests and dashboard autostart

That's it for the guided path. The rest of this section covers what the script does manually, if you prefer to configure it yourself.

---

### Manual setup (optional)

#### Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` — minimum required keys for SQLite mode:

```
STORAGE=sqlite
DEVICE_HOST=my-pi          # label shown in dashboard
DEVICE_ADDRESS=home        # location label
MONITOR_SERVER_IDS=8018,12919,31861   # comma-separated Ookla server IDs
```

Leave all `INFLUXDB_*` keys blank — they are not used in SQLite mode.

#### Run a test

```bash
python3 speedwatch.py --test-write   # verify DB write works
python3 speedwatch.py                # run one speed test
```

Results are written to `var/speeds.db`.

#### View the dashboard

```bash
python3 dashboard.py
```

Open `http://localhost:8080` in a browser.

To start the dashboard automatically on reboot, add to crontab:

```
@reboot cd /path/to/speedwatch && python3 dashboard.py >> log/dashboard.log 2>&1
```

#### Schedule speed tests

```bash
crontab -e
```

Add (runs every 30 minutes):

```
*/30 * * * * cd /path/to/speedwatch && python3 speedwatch.py >> log/cron.log 2>&1
```

---

## Multi-location setup (InfluxDB + Grafana)

The recommended order is to **collect all your credentials first** (Parts 1 and 2), then
configure the Pi in one sitting (Part 3), and finally connect Grafana (Part 4).
This avoids switching back and forth mid-setup.

---

## Part 1 — InfluxDB Cloud (free Serverless account)

### 1.1 Create account

1. Go to **influxdata.com/influxdb-signup** and fill in the sign-up form
   - **Company name:** your name or anything (required but not significant)
   - **Organisation:** use `speedwatch` (this names your InfluxDB organisation/project)
2. Sign up with email or Google/GitHub
3. On the next page, click **Keep** to stay on the free tier
4. Complete email verification if required

### 1.2 Create a bucket

A bucket is where your time-series data is stored.

1. After login you land in the **Resource Center**
2. Expand **Manage Databases & Security** and click **GO TO BUCKETS**
3. Click **CREATE BUCKET**
4. Name it `speedwatch` — this will be your `INFLUXDB_BUCKET` value
5. Click **Create**
6. On the Buckets page, note down the **bucket ID** shown next to the bucket name
   (it looks like a hex string, e.g. `a1b2c3d4e5f6a1b2`) — you will need this when
   connecting Grafana in Part 4

### 1.3 Create an API token

1. Go to **Load Data → API Tokens**
2. Click **+ Generate API Token → All Access Token**
   > **Note:** A custom token scoped to a single bucket will not work — the v1
   > compatibility API requires the broader permissions that only an All Access token provides.
3. Copy the token immediately — it won't be shown again
4. This is your `INFLUXDB_TOKEN` value

### 1.4 Find your InfluxDB URL

1. While logged in to InfluxDB Cloud, look at your browser's address bar
2. The URL will be formatted as `https://<region>.aws.cloud2.influxdata.com`
3. The **host** part (without `https://`) is your `INFLUXDB_URL` value, e.g.:
   `eu-central-1-1.aws.cloud2.influxdata.com`

> **Note:** InfluxDB Cloud Serverless automatically supports the v1 compatibility
> API that this project uses. No extra configuration is needed.
>
> You may notice a bucket called `speedwatch/autogen` appear in the UI after the
> first write. This is a normal v1→v2 compatibility mapping (DBRP) and can be ignored —
> your data is stored in the `speedwatch` bucket.

### Credentials checklist

Before moving on, make sure you have noted down:

- [ ] `INFLUXDB_URL` — host only, no `https://`
- [ ] `INFLUXDB_TOKEN` — all-access token
- [ ] `INFLUXDB_BUCKET` — `speedwatch` (or whatever you named it)
- [ ] Bucket ID — the hex ID from the Buckets page (needed for Grafana in Part 4)

---

## Part 2 — Grafana Cloud (free account)

### 2.1 Create account

1. Go to **grafana.com** and click **Create free account**
2. Sign up with email or GitHub/Google
3. You get a hosted Grafana instance at `https://yourname.grafana.net`

No further configuration is needed here yet — you will connect InfluxDB as a data
source in Part 4, after the Pi is set up and sending data.

---

## Part 3 — Set up the Pi

### 3.1 Install the speedtest CLI

```bash
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt install speedtest
speedtest --version
```

### 3.2 Download speedwatch and install dependencies

```bash
git clone https://github.com/aragno-tech/speedwatch
cd speedwatch
pip3 install -r requirements.txt
```

> On Raspberry Pi OS (Bookworm), if pip3 gives a "externally managed environment" error:
> `pip3 install -r requirements.txt --user`

### 3.3 Configure `.env`

```bash
cp .env.example .env
```

Edit `.env` with the credentials from your checklist:

```
STORAGE=influxdb
INFLUXDB_URL=eu-central-1-1.aws.cloud2.influxdata.com   # host only, no https://
INFLUXDB_TOKEN=your_all_access_token_here
INFLUXDB_BUCKET=speedwatch
DEVICE_HOST=pi-home        # label for this device
DEVICE_ADDRESS=home        # location label
MONITOR_SERVER_IDS=8018,12919,31861
```

### 3.4 Verify the connection

```bash
python3 speedwatch.py --test-write
# Expected: influxdb write OK
```

Then in InfluxDB Cloud, go to **Data Explorer**, select your bucket and the
`Ookla` measurement — you should see a data point appear.

### 3.5 Schedule speed tests

```bash
crontab -e
```

Add (runs every 30 minutes):

```
*/30 * * * * cd /path/to/speedwatch && python3 speedwatch.py >> log/cron.log 2>&1
```

---

## Part 4 — Connect Grafana to InfluxDB

### 4.1 Add InfluxDB as a data source

1. In Grafana, go to **Connections → Data sources**
2. Click **+ Add new data source**
3. Search for and select **InfluxDB**
4. Configure:

| Field | Value |
|-------|-------|
| Query language | **InfluxQL** |
| URL | `https://eu-central-1-1.aws.cloud2.influxdata.com` (full URL with `https://`) |
| Database | `speedwatch` (your bucket name) |
| User | your bucket ID (the hex ID from Part 1 step 1.2) |
| Password | your all-access API token |
| HTTP Method | GET |

5. Click **Save & Test** — you should see a green "datasource is working" message

> The bucket ID (not the bucket name) goes in the User field. Find it on the InfluxDB
> Buckets page. The API token goes in Password.

### 4.2 Create a dashboard

1. Click **+** in the sidebar → **New dashboard**
2. Click **+ Add visualization**
3. Select your InfluxDB data source

For each panel, switch to **Code** mode in the query editor and enter one of these queries:

**Download speed**
```sql
SELECT "download" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

**Upload speed**
```sql
SELECT "upload" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

**Ping and jitter**
```sql
SELECT "ping", "jitter" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

**Packet loss**
```sql
SELECT "ploss" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

Select **Time series** visualization for each panel, give it a title, and save.

---

## Finding Ookla server IDs

Both modes use `MONITOR_SERVER_IDS` to define a pool of preferred servers.

```bash
speedtest -L
```

Pick stable servers geographically close to you and add their IDs as a comma-separated list:

```
MONITOR_SERVER_IDS=8018,12919,31861
```

---

## Data Reference

The speedwatch script writes to InfluxDB with this structure:

| Element | Value |
|---------|-------|
| Measurement | `Ookla` |
| Tag: host | hostname of the Pi |
| Tag: address | location label (from `.env`) |
| Tag: server | e.g. `NextGenTel AS - Oslo (id: 8018)` |
| Field: download | Mbps (float) |
| Field: upload | Mbps (float) |
| Field: ping | milliseconds (float) |
| Field: jitter | milliseconds (float) |
| Field: ploss | percent (float) |
