import time
import random
import socket

from shared.packet_format import pack
from shared.crypto_utils import encrypt
from shared.fec_utils import fec_encode
from shared.config_utils import load_simurf_config

# --------------------------------------------------
# Load config
# --------------------------------------------------
cfg = load_simurf_config()
USE_FEC = cfg.get("use_fec", False)

# --------------------------------------------------
# Network config - FIXED FOR PROPER ROUTING
# --------------------------------------------------
# The simulator runs on HOST, listening on port 5000
SIMULATOR_HOST = "host.docker.internal"
SIMULATOR_PORT = 5000

# Application-level addressing (for packet headers)
SRC_IP = "10.0.0.2"
DST_IP = "10.0.0.1"

# --------------------------------------------------
# Message batches (DEMO-FRIENDLY)
# --------------------------------------------------
MESSAGE_BATCHES = {
    "short": [
        "Hello",
        "Wireless",
        "SimURF",
        "Demo"
    ],
    "medium": [
        "Hello from SimURF wireless transmission demo",
        "This message passes through a Rayleigh channel"
    ],
    "random": [
        "".join(
            random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
            for _ in range(random.randint(20, 80))
        )
        for _ in range(5)
    ]
}

# --------------------------------------------------
# Send packets
# --------------------------------------------------
seq = 0

print("=" * 60)
print("[Sender] Starting SimURF Wireless Transmission")
print(f"[Sender] Target: {SIMULATOR_HOST}:{SIMULATOR_PORT} (MATLAB Simulator)")
print(f"[Sender] FEC enabled: {USE_FEC}")
print("=" * 60)

for batch_name, messages in MESSAGE_BATCHES.items():
    print(f"\n[Sender] ════════ Batch: {batch_name} ════════")

    for msg in messages:
        timestamp_ns = time.time_ns()

        print(f"\n[Sender] Packet #{seq}")
        print(f"[Sender] Original message: '{msg}'")

        # -----------------------------
        # Encrypt
        # -----------------------------
        ciphertext = encrypt(msg.encode())
        print(f"[Sender] → Encrypted: {len(ciphertext)} bytes")

        # -----------------------------
        # Optional FEC
        # -----------------------------
        if USE_FEC:
            payload = fec_encode(ciphertext, repeat=3)
            print(f"[Sender] → FEC encoded: {len(payload)} bytes (3x repetition)")
        else:
            payload = ciphertext
            print(f"[Sender] → No FEC (disabled)")

        # -----------------------------
        # Pack application packet
        # -----------------------------
        pkt_bytes = pack(
            seq=seq,
            src_ip=SRC_IP,
            dst_ip=DST_IP,
            timestamp_ns=timestamp_ns,
            payload=payload
        )
        print(f"[Sender] → Packed: {len(pkt_bytes)} bytes total")

        # -----------------------------
        # CRITICAL: Use raw socket to send to simulator, NOT Scapy
        # Scapy routing was bypassing the simulator
        # -----------------------------
        try:
            # Create raw UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Send directly to simulator on host
            sock.sendto(pkt_bytes, (SIMULATOR_HOST, SIMULATOR_PORT))
            sock.close()
            
            print(f"[Sender] ✓ Sent to simulator at {SIMULATOR_HOST}:{SIMULATOR_PORT}")
        except Exception as e:
            print(f"[Sender] ✗ Send failed: {e}")

        seq += 1
        time.sleep(0.5)  # Increased delay for visibility

print("\n" + "=" * 60)
print("[Sender] All packets sent")
print("=" * 60)