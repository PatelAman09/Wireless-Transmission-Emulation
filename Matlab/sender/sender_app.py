import socket
import time

from shared.crypto_utils import encrypt
from shared.packet_format import pack

DEST = ("host.docker.internal", 5000)
SRC_IP = "10.0.0.1"
DST_IP = "10.0.0.2"

MESSAGES = [
    "Hello Secure World",
    "Wireless Systems Project",
    "MATLAB RF Simulation",
    "Encrypted Transmission",
    "BER remains zero",
    "Aman Patel Personal Project Semester 3"
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

seq = 1
print("[SENDER] Running continuously")

while True:
    for msg in MESSAGES:
        payload = encrypt(msg.encode())

        packet = pack(
            seq,
            SRC_IP,
            DST_IP,
            int(time.time() * 1e6),
            payload
        )

        print(f"[SENDER] Sending seq={seq}: {msg}")
        sock.sendto(packet, DEST)

        seq += 1
        time.sleep(1)
