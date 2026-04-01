import os
import re
import subprocess

try:
    from lib.speedwatch_lib import send_email, write_log, RECIPIENTS, SERVER_COUNT, MONITOR_SERVER_IDS
except ImportError:
    from speedwatch_lib import send_email, write_log, RECIPIENTS, SERVER_COUNT, MONITOR_SERVER_IDS

LAST_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'last_server_id')
KNOWN_SERVERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'known_servers')


def fetch_server_list_from_cli():
    """Run speedtest -L and return list of {id, name} dicts in proximity order."""
    output = subprocess.Popen(
        '/usr/bin/speedtest -L --accept-license --accept-gdpr',
        shell=True, stdout=subprocess.PIPE
    ).stdout.read().decode('utf-8')
    servers = []
    past_header = False
    for line in output.splitlines():
        if line.startswith('='):
            past_header = True
            continue
        if not past_header or not line.strip():
            continue
        parts = re.split(r'\s{2,}', line.strip())
        if len(parts) >= 3:
            servers.append({'id': parts[0], 'name': f"{parts[1]} - {parts[2]}"})
    return servers


def read_last_server_id():
    """Return the last used server ID, or None if no history exists."""
    if os.path.isfile(LAST_SERVER_PATH):
        with open(LAST_SERVER_PATH, 'r') as f:
            return f.read().strip() or None
    return None


def write_last_server_id(server_id):
    with open(LAST_SERVER_PATH, 'w') as f:
        f.write(server_id)


def read_known_servers():
    """Return a set of previously seen server IDs. Supports 'id' and 'id - name' formats."""
    if os.path.isfile(KNOWN_SERVERS_PATH):
        with open(KNOWN_SERVERS_PATH, 'r') as f:
            return set(line.split(' - ')[0].strip() for line in f if line.strip())
    return set()


def record_known_server(server_id, server_name):
    with open(KNOWN_SERVERS_PATH, 'a') as f:
        f.write(f"{server_id} - {server_name}\n")


def get_server_candidates():
    """
    Returns (preferred, fallbacks) with no side effects.

    preferred  -- {id, name} dict for the next server in the preferred rotation
    fallbacks  -- list of {id, name} dicts for all non-preferred servers from speedtest -L
    """
    servers = fetch_server_list_from_cli()
    server_map = {s['id']: s for s in servers}

    if MONITOR_SERVER_IDS:
        # Explicit preferred pool from config; fall back to placeholder name if not in -L
        preferred_pool = [
            server_map.get(sid, {'id': sid, 'name': f'server {sid}'})
            for sid in MONITOR_SERVER_IDS
        ]
        preferred_ids = set(MONITOR_SERVER_IDS)
        fallback_pool = [s for s in servers if s['id'] not in preferred_ids]
    else:
        # No explicit preferred list — use first SERVER_COUNT servers from -L
        preferred_pool = servers[:SERVER_COUNT]
        preferred_ids = {s['id'] for s in preferred_pool}
        fallback_pool = [s for s in servers if s['id'] not in preferred_ids]

    if not preferred_pool:
        raise RuntimeError("No preferred servers available")

    last_id = read_last_server_id()
    ids = [s['id'] for s in preferred_pool]
    next_index = (ids.index(last_id) + 1) % len(preferred_pool) if last_id in ids else 0

    return preferred_pool[next_index], fallback_pool


def record_server_used(server_id, server_name):
    """
    Called after a successful test. Advances the rotation and sends a
    new-server notification email if this server has not been seen before.
    """
    write_last_server_id(server_id)

    known = read_known_servers()
    if server_id not in known:
        record_known_server(server_id, server_name)
        write_log(f"(New server) {server_id} - {server_name}")
        send_email(
            f"New speedtest server: {server_name}",
            f"Speedwatch is now rotating to a server it has not used before.\n\nServer ID: {server_id}\nServer: {server_name}\n\nYou may want to update your Grafana dashboards.",
            RECIPIENTS
        )


if __name__ == "__main__":
    preferred, fallbacks = get_server_candidates()
    print(f"Preferred: {preferred['id']} - {preferred['name']}")
    print(f"Fallbacks ({len(fallbacks)}):")
    for s in fallbacks:
        print(f"  {s['id']} - {s['name']}")
