#!/usr/bin/env bash
# speedwatch setup — single-home (SQLite) mode
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# --- helpers ---
green()  { printf '\033[0;32m  OK  \033[0m %s\n' "$*"; }
yellow() { printf '\033[1;33m WARN \033[0m %s\n' "$*"; }
die()    { printf '\033[0;31mERROR \033[0m %s\n' "$*"; exit 1; }
header() { echo ""; echo "$*"; echo "$(echo "$*" | tr '[:print:]' '-')"; }
ask()    { printf '\n\033[1m%s\033[0m\n' "$*"; }

echo ""
echo "========================================"
echo "  speedwatch setup"
echo "========================================"

# --- prerequisites ---

header "Checking prerequisites"

command -v python3 &>/dev/null \
    || die "python3 not found. Install it with: sudo apt install python3"
green "python3 found"

command -v pip3 &>/dev/null \
    || die "pip3 not found. Install it with: sudo apt install python3-pip"
green "pip3 found"

if ! command -v speedtest &>/dev/null; then
    echo ""
    echo "  speedtest CLI not found. Install it from Ookla, then re-run this script:"
    echo ""
    echo "    curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh | sudo bash"
    echo "    sudo apt install speedtest"
    echo ""
    exit 1
fi
green "speedtest CLI found"

# --- python dependencies ---

header "Installing Python dependencies"

if pip3 install -r requirements.txt -q 2>/dev/null; then
    green "Dependencies installed"
elif pip3 install -r requirements.txt --user -q 2>/dev/null; then
    green "Dependencies installed (user install)"
else
    die "pip install failed. Try manually: pip3 install -r requirements.txt --break-system-packages"
fi

mkdir -p var log
green "Directories ready (var/, log/)"

# --- .env configuration ---

if [ -f .env ]; then
    echo ""
    yellow ".env already exists — skipping configuration. Edit it manually to change settings."
else
    header "Configuration"

    ask "What should this device be called in the dashboard?"
    echo "  (e.g. home-pi, kitchen-pi — press Enter for 'speedwatch-pi')"
    read -r DEVICE_HOST
    [ -z "$DEVICE_HOST" ] && DEVICE_HOST="speedwatch-pi"

    ask "Location label for this device?"
    echo "  (e.g. home, upstairs — press Enter for 'home')"
    read -r DEVICE_ADDRESS
    [ -z "$DEVICE_ADDRESS" ] && DEVICE_ADDRESS="home"

    ask "Fetching nearby Ookla servers..."
    echo ""
    speedtest -L 2>/dev/null | head -25 || true
    echo ""
    ask "Enter the server IDs you want to use (comma-separated, e.g. 8018,12919):"
    echo "  Tip: pick 2-3 servers geographically close to you."
    read -r MONITOR_SERVER_IDS

    ask "Email alerts? Enter sender address or press Enter to skip:"
    read -r EMAIL_SENDER

    EMAIL_PASSWORD=""
    EMAIL_RECIPIENTS=""
    if [ -n "$EMAIL_SENDER" ]; then
        ask "Email app password (input hidden):"
        read -rs EMAIL_PASSWORD
        echo ""
        ask "Alert recipient address(es), comma-separated:"
        read -r EMAIL_RECIPIENTS
    fi

    cat > .env <<EOF
# Device identity
DEVICE_HOST=${DEVICE_HOST}
DEVICE_ADDRESS=${DEVICE_ADDRESS}

# Storage
STORAGE=sqlite
SQLITE_MAX_ROWS=10000
DASHBOARD_PORT=8080

# Speed test servers (comma-separated Ookla server IDs)
MONITOR_SERVER_IDS=${MONITOR_SERVER_IDS}
SERVER_COUNT=3

# Email alerts (leave blank to disable)
EMAIL_SENDER=${EMAIL_SENDER}
EMAIL_PASSWORD=${EMAIL_PASSWORD}
EMAIL_RECIPIENTS=${EMAIL_RECIPIENTS}

# Logging
LOG=true
LOG_MAX_BYTES=1048576
LOG_BACKUP_COUNT=3
DEBUG=false

# Ping test
PING_COUNT=10

# InfluxDB (not used in sqlite mode)
INFLUXDB_TOKEN=
INFLUXDB_URL=
INFLUXDB_ORG=
INFLUXDB_USER=
INFLUXDB_BUCKET=speedwatch
EOF

    green ".env created"
fi

# --- verify storage ---

header "Verifying database"

if python3 speedwatch.py --test-write; then
    green "Database write OK — var/speeds.db is ready"
else
    die "Test write failed. Check your .env and try again."
fi

# --- cron setup ---

header "Scheduling"

add_cron_line() {
    local line="$1"
    local existing
    existing=$(crontab -l 2>/dev/null || true)
    if echo "$existing" | grep -qF "$line"; then
        yellow "Cron entry already exists — skipping"
    else
        (echo "$existing"; echo "$line") | crontab -
        green "Cron entry added"
    fi
}

ask "Run a speed test every 30 minutes? (y/N)"
read -r SETUP_CRON
if [[ "${SETUP_CRON,,}" == "y" ]]; then
    add_cron_line "*/30 * * * * cd ${SCRIPT_DIR} && python3 speedwatch.py >> log/cron.log 2>&1"
fi

ask "Start the dashboard automatically on reboot? (y/N)"
read -r SETUP_DASHBOARD
if [[ "${SETUP_DASHBOARD,,}" == "y" ]]; then
    add_cron_line "@reboot cd ${SCRIPT_DIR} && python3 dashboard.py >> log/dashboard.log 2>&1"
fi

# --- done ---

echo ""
echo "========================================"
green "Setup complete."
echo ""
echo "  Run a speed test now:   python3 speedwatch.py"
echo "  Start the dashboard:    python3 dashboard.py"
echo "  Then open:              http://localhost:8080"
echo "========================================"
echo ""
