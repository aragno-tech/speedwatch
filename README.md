# speedwatch

Automated internet speed monitoring for Raspberry Pi (or any Linux box).

---

## Why this exists

My internet connection was unstable — drops, slowdowns, the usual. When I called support, the answer was always "everything looks fine on our end." Talking to neighbours, they had the same experience. Nobody had data, just complaints.

So I set up a Raspberry Pi to run automated speed tests around the clock. When I sat down with support and showed them a chart of degraded performance over weeks — times, dates, measured values — the conversation changed. The fault was found and fixed quickly.

A neighbour wanted the same setup. That's when the multi-location mode (InfluxDB + Grafana) was added, so several households could feed into one shared dashboard. The simpler single-device mode is for anyone who just wants to monitor their own connection without cloud accounts.

If you're having the same argument with your ISP, maybe this helps.

---

## What it does

- Runs `speedtest` on a cron schedule
- Rotates between a pool of preferred Ookla servers
- Writes results to SQLite (local) or InfluxDB (cloud)
- Built-in browser dashboard for SQLite mode; Grafana for InfluxDB mode
- Optional email alerts when a new server is used or results look unusual

---

## Modes

|                         | Single-home (SQLite)         | Multi-location (InfluxDB)          |
|-------------------------|------------------------------|------------------------------------|
| Storage                 | Local file (`var/speeds.db`) | InfluxDB Cloud (free tier)         |
| Dashboard               | Built-in (`dashboard.py`)    | Grafana Cloud                      |
| Cloud accounts required | No                           | Yes                                |
| Best for                | One device, no cloud         | Multiple devices, shared dashboard |

---

## Quick start

**Step 1 — Install the Ookla speedtest CLI** (required by both modes):

```bash
curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash
sudo apt install speedtest
```

**Step 2 — Download and run setup:**

```bash
git clone https://github.com/aragno-tech/speedwatch
cd speedwatch
bash setup.sh
```

The setup script installs dependencies, walks you through configuration, and optionally sets up cron.

For the multi-location mode (InfluxDB + Grafana) or manual setup: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## Requirements

- Raspberry Pi or any Linux box
- Python 3
- [Ookla speedtest CLI](https://www.speedtest.net/apps/cli)

---

## Other tools

| Script | What it does |
|---|---|
| `lib/pingtest.py` | Periodic ping tests to configured hosts |
| `lib/notify_ip_change.py` | Emails you when your public IP changes |
