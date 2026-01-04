import socket
import sys

from shared.packet_format import unpack
from shared.crypto_utils import decrypt
from shared.fec_utils import fec_decode
from shared.config_utils import load_simurf_config

# --------------------------------------------------
# Load configuration
# --------------------------------------------------
try:
    cfg = load_simurf_config()
    USE_FEC = cfg.get("use_fec", False)
except Exception as e:
    print(f"[Receiver] WARNING: Could not load config: {e}")
    USE_FEC = False

# --------------------------------------------------
# Network configuration
# --------------------------------------------------
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000      # inside container

BUFFER_SIZE = 65535

# --------------------------------------------------
# UDP socket
# --------------------------------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    sock.bind((LISTEN_IP, LISTEN_PORT))
    print("=" * 60)
    print(f"[Receiver] ✓ Successfully bound to {LISTEN_IP}:{LISTEN_PORT}")
    print(f"[Receiver] FEC enabled: {USE_FEC}")
    print(f"[Receiver] Waiting for packets...")
    print("=" * 60)
    sys.stdout.flush()
except Exception as e:
    print(f"[Receiver] ✗ ERROR: Could not bind socket: {e}")
    sys.exit(1)

# --------------------------------------------------
# Statistics
# --------------------------------------------------
packet_count = 0
success_count = 0
crc_errors = 0
decode_errors = 0

# --------------------------------------------------
# Main receive loop
# --------------------------------------------------
while True:
    try:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        packet_count += 1
        
        # Always print raw receipt
        print(f"\n[Receiver] ════════════════════════════════════")
        print(f"[Receiver] Packet #{packet_count}: Received from {addr}")
        print(f"[Receiver] Raw size: {len(data)} bytes")
        sys.stdout.flush()

        try:
            # -----------------------------
            # Unpack + CRC validation
            # -----------------------------
            pkt = unpack(data)
            print(f"[Receiver] ✓ CRC valid, SEQ={pkt['seq']}")
            print(f"[Receiver]   SRC={pkt['src_ip']} → DST={pkt['dst_ip']}")
            print(f"[Receiver]   Payload size: {len(pkt['payload'])} bytes")
            
            payload = pkt["payload"]

            # -----------------------------
            # Optional FEC decoding
            # -----------------------------
            if USE_FEC:
                print(f"[Receiver] → Decoding FEC...")
                try:
                    payload = fec_decode(payload, repeat=3)
                    print(f"[Receiver] ✓ FEC decoded: {len(payload)} bytes")
                except Exception as e:
                    print(f"[Receiver] ✗ FEC decode failed: {e}")
                    raise

            # -----------------------------
            # Decrypt payload
            # -----------------------------
            print(f"[Receiver] → Decrypting...")
            try:
                plaintext = decrypt(payload)
                print(f"[Receiver] ✓ Decrypted: {len(plaintext)} bytes")
            except Exception as e:
                print(f"[Receiver] ✗ Decryption failed: {e}")
                raise

            # -----------------------------
            # Decode message
            # -----------------------------
            try:
                msg = plaintext.decode(errors="replace")
                print(f"[Receiver] ✓ MESSAGE: '{msg}'")
                success_count += 1
            except Exception as e:
                print(f"[Receiver] ✗ UTF-8 decode failed: {e}")
                print(f"[Receiver]   Raw bytes: {plaintext[:50]}...")
                raise

        except ValueError as e:
            # CRC or length corruption
            crc_errors += 1
            print(f"[Receiver] ✗ CORRUPTED (CRC/length): {e}")

        except Exception as e:
            # Any other decode issue
            decode_errors += 1
            print(f"[Receiver] ✗ DECODE ERROR: {e}")

        # Print statistics
        print(f"[Receiver] Stats: {success_count} OK | {crc_errors} CRC | {decode_errors} Decode")
        print(f"[Receiver] ════════════════════════════════════\n")
        sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n[Receiver] Shutting down...")
        break
    except Exception as e:
        print(f"[Receiver] ✗ Unexpected error in main loop: {e}")
        sys.stdout.flush()