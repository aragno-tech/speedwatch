import os
import xml.etree.ElementTree as ET
import requests

try:
    from lib.speedwatch_lib import send_email, write_log, RECIPIENTS, SERVER_COUNT, FALLBACK_COUNT
except ImportError:
    from speedwatch_lib import send_email, write_log, RECIPIENTS, SERVER_COUNT, FALLBACK_COUNT

OOKLA_STATIC_URL = "https://c.speedtest.net/speedtest-servers-static.php"
LAST_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'last_server_id')
KNOWN_SERVERS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'var', 'known_servers')


def fetch_server_list():
    """Fetch SERVER_COUNT + FALLBACK_COUNT servers from the Ookla static list as [{id, name}]."""
    response = requests.get(OOKLA_STATIC_URL, timeout=10)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    servers = []
    total = SERVER_COUNT + FALLBACK_COUNT
    for server in root.iter('server'):
        servers.append({
            'id': server.attrib['id'],
            'name': f"{server.attrib.get('sponsor', '')} ({server.attrib.get('name', '')}, {server.attrib.get('country', '')})"
        })
        if len(servers) >= total:
            break
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
    fallbacks  -- list of {id, name} dicts for servers beyond SERVER_COUNT (tried if preferred fails)
    """
    servers = fetch_server_list()
    if not servers:
        raise RuntimeError("No servers returned from Ookla static list")

    preferred_pool = servers[:SERVER_COUNT]
    fallback_pool = servers[SERVER_COUNT:]

    last_id = read_last_server_id()
    ids = [s['id'] for s in preferred_pool]

    if last_id in ids:
        next_index = (ids.index(last_id) + 1) % len(preferred_pool)
    else:
        next_index = 0

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
