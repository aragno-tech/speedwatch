"""
Local web dashboard for speedwatch SQLite mode.
Usage: python3 dashboard.py
Configure port via DASHBOARD_PORT in .env (default 8080).
"""

import http.server
import json
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

PORT = int(os.getenv("DASHBOARD_PORT", "8080"))

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>speedwatch</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  body { font-family: sans-serif; background: #111; color: #eee; margin: 0; padding: 1rem 2rem; }
  h1 { font-size: 1.4rem; margin-bottom: 1.5rem; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }
  .card { background: #1c1c1c; border-radius: 8px; padding: 1rem; }
  canvas { width: 100% !important; }
  @media (max-width: 700px) { .grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<h1>speedwatch</h1>
<div class="grid">
  <div class="card"><canvas id="download"></canvas></div>
  <div class="card"><canvas id="upload"></canvas></div>
  <div class="card"><canvas id="ping"></canvas></div>
  <div class="card"><canvas id="servers"></canvas></div>
</div>
<script>
const CHART_DEFAULTS = {
  responsive: true,
  animation: false,
  plugins: { legend: { labels: { color: '#ccc' } } },
  scales: {
    x: { ticks: { color: '#888', maxTicksLimit: 8 }, grid: { color: '#333' } },
    y: { ticks: { color: '#888' }, grid: { color: '#333' } }
  }
};

function lineChart(id, label, color, labels, values, unit) {
  new Chart(document.getElementById(id), {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: label + (unit ? ' (' + unit + ')' : ''),
        data: values,
        borderColor: color,
        backgroundColor: color + '22',
        borderWidth: 2,
        pointRadius: 2,
        fill: true,
        tension: 0.3
      }]
    },
    options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins,
      title: { display: true, text: label, color: '#eee' } } }
  });
}

fetch('/data').then(r => r.json()).then(rows => {
  if (!rows.length) {
    document.querySelector('h1').textContent += ' — no data yet';
    return;
  }

  // Rows arrive newest-first; reverse for chronological charts
  const asc = [...rows].reverse();
  const labels = asc.map(r => r.timestamp.replace('T', ' ').replace('Z', ''));

  lineChart('download', 'Download', '#4fc3f7', labels, asc.map(r => r.download), 'Mbps');
  lineChart('upload',   'Upload',   '#81c784', labels, asc.map(r => r.upload),   'Mbps');
  lineChart('ping',     'Ping',     '#ffb74d', labels, asc.map(r => r.ping),     'ms');

  // Per-server bar chart: average download per server label
  const serverMap = {};
  rows.forEach(r => {
    if (!serverMap[r.server]) serverMap[r.server] = [];
    serverMap[r.server].push(r.download);
  });
  const serverKeys = Object.keys(serverMap);
  const serverNames = serverKeys.map(s => s.replace(/ \(id: \d+\)$/, ''));
  const serverAvgs = serverKeys.map(s => {
    const vals = serverMap[s];
    return (vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(2);
  });
  const palette = ['#4fc3f7','#81c784','#ffb74d','#e57373','#ba68c8','#4db6ac'];
  new Chart(document.getElementById('servers'), {
    type: 'bar',
    data: {
      labels: serverNames,
      datasets: [{
        label: 'Avg Download (Mbps)',
        data: serverAvgs,
        backgroundColor: serverNames.map((_, i) => palette[i % palette.length])
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: { ...CHART_DEFAULTS.plugins,
        title: { display: true, text: 'Avg Download by Server', color: '#eee' },
        legend: { display: false }
      }
    }
  });
});
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress per-request console noise

    def do_GET(self):
        if self.path == '/data':
            self._serve_data()
        elif self.path in ('/', '/index.html'):
            self._serve_html()
        else:
            self.send_error(404)

    def _serve_html(self):
        body = _HTML.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_data(self):
        import lib.storage_sqlite as _sq
        records = _sq.read_records(limit=500)
        body = json.dumps(records).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = http.server.HTTPServer(('', PORT), Handler)
    print(f'speedwatch dashboard → http://localhost:{PORT}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
