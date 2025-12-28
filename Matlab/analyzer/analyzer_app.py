from flask import Flask, jsonify, render_template_string
import os

LOG_FILE = "/logs/receiver.log"
MAX_LINES = 50

app = Flask(__name__)


def read_logs():
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, "r") as f:
        lines = f.readlines()[-MAX_LINES:]

    rows = []
    for line in lines:
        try:
            seq, enc, dec, ber = line.strip().split("|")
            rows.append({
                "seq": seq,
                "encrypted": enc + "...",
                "decrypted": dec,
                "ber": ber
            })
        except ValueError:
            continue

    return rows


@app.route("/api/messages")
def api_messages():
    return jsonify(read_logs())


@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
  <title>SimuRF Dashboard</title>
  <script>
    async function load() {
      const r = await fetch('/api/messages');
      const d = await r.json();
      document.getElementById('t').innerHTML =
        d.map(m => `
          <tr>
            <td>${m.seq}</td>
            <td>${m.encrypted}</td>
            <td>${m.decrypted}</td>
            <td>${m.ber}</td>
          </tr>
        `).join('');
    }
    setInterval(load, 1000);
    load();
  </script>
</head>
<body>
  <h1>SimuRF Dashboard</h1>
  <table border="1">
    <tr><th>Seq</th><th>Encrypted</th><th>Decrypted</th><th>BER</th></tr>
    <tbody id="t"></tbody>
  </table>
</body>
</html>
""")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
