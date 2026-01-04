import socket
import json

LISTEN_IP = "0.0.0.0"
METRICS_PORT = 7000
BUFFER_SIZE = 65535

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, METRICS_PORT))

print("[Analyzer] Listening for metrics on port 7000", flush=True)

while True:
    data, addr = sock.recvfrom(BUFFER_SIZE)

    metrics = json.loads(data.decode())

    print(
        f"[Analyzer] Metrics received: {metrics}",
        flush=True
    )
