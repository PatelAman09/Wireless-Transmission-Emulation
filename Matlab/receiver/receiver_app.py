import socket
import os
from shared.packet_format import unpack
from shared.crypto_utils import decrypt

LOG_DIR = "/logs"
LOG_FILE = "/logs/receiver.log"

os.makedirs(LOG_DIR, exist_ok=True)

LISTEN_ADDR = ("0.0.0.0", 6000)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(LISTEN_ADDR)

print("[RECEIVER] Listening")

while True:
    data, addr = sock.recvfrom(4096)

    pkt = unpack(data)

    try:
        decrypted = decrypt(pkt["payload"]).decode(errors="replace")
    except Exception:
        decrypted = "[DECRYPT ERROR]"

    encrypted_hex = pkt["payload"].hex()[:32]

    ber = pkt.get("ber", 0.0)

    # ---- WRITE TO LOG (dashboard reads this) ----
    with open(LOG_FILE, "a") as f:
        f.write(
            f"{pkt['seq']}|{encrypted_hex}|{decrypted}|{ber}\n"
        )

    # ---- Console output ----
    print(f"[RECEIVER] seq={pkt['seq']} decrypted={decrypted}")
