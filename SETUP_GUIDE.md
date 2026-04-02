# Speedwatch: InfluxDB + Grafana Setup Guide

This guide walks through creating free cloud accounts for InfluxDB and Grafana,
connecting them together, and building a basic speedtest dashboard.

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

---

## Part 2 — Configure `.env`

Edit `/home/netmon/speedwatch/.env` (create from `.env.example` if it doesn't exist):

```
INFLUXDB_URL=us-east-1-1.aws.cloud2.influxdata.com   # host only, no https://
INFLUXDB_TOKEN=your_token_here
INFLUXDB_BUCKET=speedwatch                             # must match bucket name
```

### 2.1 Verify the connection

Run a manual speedtest to confirm data lands in InfluxDB:

```bash
cd /home/netmon/speedwatch
python3 speedwatch.py -v
```

Then in InfluxDB Cloud, go to **Data Explorer**, select your bucket and the
`Ookla` measurement — you should see a data point within a minute or two.

---

## Part 3 — Grafana Cloud (free account)

### 3.1 Create account

1. Go to **grafana.com** and click **Create free account**
2. Sign up with email or GitHub/Google
3. You get a hosted Grafana instance at `https://yourname.grafana.net`

### 3.2 Add InfluxDB as a data source

1. In Grafana, go to **Connections → Data sources** (or **Configuration → Data Sources**)
2. Click **+ Add new data source**
3. Search for and select **InfluxDB**
4. Configure:

| Field | Value |
|-------|-------|
| Query language | **InfluxQL** |
| URL | `https://us-east-1-1.aws.cloud2.influxdata.com` (your full URL with https://) |
| Database | `speedwatch` (your bucket name) |
| User | bucket ID (copy from the InfluxDB Buckets page — the hex ID next to your bucket name) |
| Password | paste your InfluxDB API token |
| HTTP Method | GET |

5. Click **Save & Test** — you should see a green "datasource is working" message

> The project uses the InfluxDB v1 compatibility API. The bucket ID in User and
> the API token in Password are both required for Grafana to authenticate correctly.

---

## Part 4 — Create a Dashboard

### 4.1 New dashboard

1. Click **+** in the sidebar → **New dashboard**
2. Click **+ Configure**

### 4.2 Download speed panel

1. Select your InfluxDB data source
2. Switch to **Code** mode in the query editor (click the small pencil icon)
3. Enter:

```sql
SELECT "download" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

4. Select **Time series** visualization
5. Set **Panel title** to `Download Speed`
6. Hit **Save**, then navigate back to the dashboard

### 4.3 Upload speed panel

1. Click **Add new element** (blue + sign on the right) to add a new panel
2. Select your InfluxDB data source
3. Switch to **Code** mode in the query editor (click the small pencil icon)
4. Enter:

```sql
SELECT "upload" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

5. Select **Time series** visualization
6. Set **Panel title** to `Upload Speed`
7. Hit **Save**, then navigate back to the dashboard

### 4.4 Ping / latency panel

1. Click **Add new element** (blue + sign on the right) to add a new panel
2. Select your InfluxDB data source
3. Switch to **Code** mode in the query editor (click the small pencil icon)
4. Enter:

```sql
SELECT "ping", "jitter" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

5. Select **Time series** visualization
6. Set **Panel title** to `Ping & Jitter`
7. Hit **Save**, then navigate back to the dashboard

### 4.5 Packet loss panel

1. Click **Add new element** (blue + sign on the right) to add a new panel
2. Select your InfluxDB data source
3. Switch to **Code** mode in the query editor (click the small pencil icon)
4. Enter:

```sql
SELECT "ploss" FROM "Ookla" WHERE $timeFilter GROUP BY "server"::tag
```

5. Select **Time series** visualization
6. Set **Panel title** to `Packet Loss`
7. Hit **Save**, then navigate back to the dashboard

---

## Data Reference

The speedwatch script writes to InfluxDB with this structure:

| Element | Value |
|---------|-------|
| Measurement | `Ookla` |
| Tag: host | hostname of the Pi |
| Tag: address | IP address (from `.env`) |
| Tag: server | e.g. `NextGenTel AS - Oslo (id: 8018)` |
| Field: download | Mbps (float) |
| Field: upload | Mbps (float) |
| Field: ping | milliseconds (float) |
| Field: jitter | milliseconds (float) |
| Field: ploss | percent (float) |
