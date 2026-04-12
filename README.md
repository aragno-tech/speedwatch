# speedwatch

Monitor internet speed over time on a Raspberry Pi — or any Linux box. Logs every result to a database, shows trends in a dashboard, and gives you real data to bring to your ISP.

---

## Why this exists

My internet connection was unstable — drops, slowdowns, the usual. When I called support, the answer was always "everything looks fine on our end." Support could never reproduce it — the drops happened at odd hours, and intermittent faults are hard to catch in real-time. Talking to neighbors, I realized they had the same experience. Nobody had data, just complaints.

So I set up a Raspberry Pi to run automated speed tests around the clock, logging the results to an InfluxDB database and displaying them in Grafana. Multi-location monitoring was part of the design from day one, so it was straightforward to add a second device at a neighbor's house feeding the same shared dashboard.

When I finally sat down with support and showed them a chart of degraded performance over several weeks — complete with precise times, dates, and measured values — the conversation changed instantly. With concrete data on the table, the fault was identified and fixed quickly.

However, the value of the setup didn't end there. Because the neighborhood had struggled with instability for so long, many neighbors remained suspicious and were quick to blame the ISP every time they experienced a glitch. By deploying a Pi to their homes, we could quickly determine if the issue was a legitimate line fault or simply a local Wi-Fi bottleneck.

Most of the time, the data now shows that the ISP is delivering as promised, and the issue lies within the home network. These devices have been running ever since, providing us with peace of mind and the confidence of knowing exactly who to call when things go wrong.

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
