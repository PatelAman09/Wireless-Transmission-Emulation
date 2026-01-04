import os
import sys
import json
import socket
import matlab.engine

# --------------------------------------------------
# Path setup
# --------------------------------------------------
MATLAB_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, MATLAB_ROOT)

from shared.packet_format import unpack, pack

# --------------------------------------------------
# Resolve paths
# --------------------------------------------------
CONFIG_PATH = os.path.join(
    MATLAB_ROOT, "config", "matlab_channel_config.json"
)

MATLAB_FUNC_DIR = os.path.join(
    MATLAB_ROOT, "matlab_components"
)

print(f"[Simulator] Config path: {CONFIG_PATH}")
print(f"[Simulator] MATLAB components: {MATLAB_FUNC_DIR}")

# --------------------------------------------------
# Load channel config
# --------------------------------------------------
with open(CONFIG_PATH) as f:
    channel_cfg = json.load(f)

# --------------------------------------------------
# NETWORK CONFIG
# --------------------------------------------------
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000              # sender → simulator

# Direct to receiver container via host port mapping
RECEIVER_HOST = os.environ.get("RECEIVER_IP", "127.0.0.1")
RECEIVER_PORT = 5001             # mapped to container's 5000

ANALYZER_HOST = "127.0.0.1"
ANALYZER_METRICS_PORT = 7001

BUFFER_SIZE = 65535

print(f"[Simulator] Receiver target: {RECEIVER_HOST}:{RECEIVER_PORT}")

# --------------------------------------------------
# Start MATLAB engine
# --------------------------------------------------
print("[Simulator] Starting MATLAB engine...")
try:
    eng = matlab.engine.start_matlab()
    eng.addpath(MATLAB_FUNC_DIR, nargout=0)
    eng.init_channel(channel_cfg, nargout=0)
    print("[Simulator] MATLAB RF channel initialized")
except Exception as e:
    print(f"[Simulator] ERROR starting MATLAB: {e}")
    sys.exit(1)

# --------------------------------------------------
# UDP sockets
# --------------------------------------------------
sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_in.bind((LISTEN_IP, LISTEN_PORT))

sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock_metrics = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"[Simulator] Listening on {LISTEN_IP}:{LISTEN_PORT}")
print("[Simulator] Ready to process packets...")

# --------------------------------------------------
# Helper function to convert MATLAB types to Python
# --------------------------------------------------
def matlab_to_python(value):
    """Convert MATLAB/numpy types to Python native types for JSON"""
    if hasattr(value, 'item'):  # numpy/MATLAB scalar
        return value.item()
    elif isinstance(value, (list, tuple)):
        return [matlab_to_python(v) for v in value]
    elif isinstance(value, dict):
        return {k: matlab_to_python(v) for k, v in value.items()}
    else:
        return value

# --------------------------------------------------
# Main loop
# --------------------------------------------------
packet_count = 0

while True:
    try:
        packet_bytes, addr = sock_in.recvfrom(BUFFER_SIZE)
        packet_count += 1
        print(f"\n[Simulator] ════════════════════════════════════")
        print(f"[Simulator] Packet #{packet_count}: Received {len(packet_bytes)} bytes from {addr}")

        # -----------------------------
        # Unpack packet (CRC-safe)
        # -----------------------------
        try:
            pkt = unpack(packet_bytes)
            print(f"[Simulator] ✓ Unpacked: SEQ={pkt['seq']}, payload={len(pkt['payload'])} bytes")
        except Exception as e:
            print(f"[Simulator] ✗ Unpack failed: {e}")
            continue

        # -----------------------------
        # Apply RF channel to payload only
        # -----------------------------
        try:
            tx_payload = matlab.uint8(list(pkt["payload"]))
            print(f"[Simulator] → Applying RF channel (MATLAB)...")
            
            rx_payload, metrics = eng.rf_emulator(tx_payload, nargout=2)
            
            print(f"[Simulator] ✓ RF emulation complete")
            print(f"[Simulator]   SNR: {metrics['snr_db']} dB, Doppler: {metrics['doppler']} Hz")
            
            # Show BER if available
            if 'ber' in metrics:
                print(f"[Simulator]   BER: {metrics['ber']:.4f} ({metrics.get('bit_errors', 0)}/{metrics.get('bytes_total', 0)*8} bits)")
            
        except Exception as e:
            print(f"[Simulator] ✗ MATLAB RF emulation failed: {e}")
            continue

        # -----------------------------
        # Re-pack with impaired payload
        # -----------------------------
        try:
            new_packet = pack(
                pkt["seq"],
                pkt["src_ip"],
                pkt["dst_ip"],
                pkt["timestamp_ns"],
                bytes(rx_payload)
            )
            print(f"[Simulator] ✓ Re-packed: {len(new_packet)} bytes")
        except Exception as e:
            print(f"[Simulator] ✗ Re-pack failed: {e}")
            continue

        # -----------------------------
        # SEND TO RECEIVER
        # -----------------------------
        try:
            sock_out.sendto(new_packet, (RECEIVER_HOST, RECEIVER_PORT))
            print(f"[Simulator] ✓ Forwarded to receiver at {RECEIVER_HOST}:{RECEIVER_PORT}")
        except Exception as e:
            print(f"[Simulator] ✗ Forward to receiver failed: {e}")

        # -----------------------------
        # Send metrics to analyzer (FIXED JSON SERIALIZATION)
        # -----------------------------
        try:
            # Convert all MATLAB types to Python native types
            metrics_dict = dict(metrics)  # Convert MATLAB struct to Python dict
            metrics_serializable = {}
            
            for key, value in metrics_dict.items():
                metrics_serializable[key] = matlab_to_python(value)
            
            metrics_json = json.dumps(metrics_serializable)
            sock_metrics.sendto(
                metrics_json.encode(),
                (ANALYZER_HOST, ANALYZER_METRICS_PORT)
            )
            print(f"[Simulator] ✓ Metrics sent to analyzer")
        except Exception as e:
            print(f"[Simulator] ✗ Metrics send failed: {e}")
            # Print metrics dict for debugging
            print(f"[Simulator]   Debug - Metrics type: {type(metrics)}")
            if isinstance(metrics, dict):
                for k, v in metrics.items():
                    print(f"[Simulator]   {k}: {v} (type: {type(v)})")

        print(f"[Simulator] ════════════════════════════════════\n")

    except KeyboardInterrupt:
        print("\n[Simulator] Shutting down...")
        break
    except Exception as e:
        print(f"[Simulator] ✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        continue

# Cleanup
sock_in.close()
sock_out.close()
sock_metrics.close()
eng.quit()
print("[Simulator] Stopped")