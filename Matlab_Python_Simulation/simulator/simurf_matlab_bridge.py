import os
import sys
import json
import socket

# Import compiled MATLAB package
import rf_channel_pkg

# --------------------------------------------------
# Path setup
# --------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from shared.packet_format import unpack, pack

# --------------------------------------------------
# Load channel config
# --------------------------------------------------
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config", "matlab_channel_config.json")

print(f"[Simulator] Config path: {CONFIG_PATH}")

with open(CONFIG_PATH) as f:
    channel_cfg = json.load(f)

# --------------------------------------------------
# NETWORK CONFIG
# --------------------------------------------------
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = 5000

# Connect to receiver container
RECEIVER_HOST = "receiver"  # Docker service name
RECEIVER_PORT = 5000

# Connect to analyzer container
ANALYZER_HOST = "analyzer"  # Docker service name
ANALYZER_PORT = 7000

BUFFER_SIZE = 65535

print(f"[Simulator] Receiver target: {RECEIVER_HOST}:{RECEIVER_PORT}")
print(f"[Simulator] Analyzer target: {ANALYZER_HOST}:{ANALYZER_PORT}")

# --------------------------------------------------
# Initialize MATLAB Runtime and RF channel
# --------------------------------------------------
print("[Simulator] Initializing MATLAB Runtime and RF channel...")
try:
    # Initialize the compiled MATLAB package
    rf_pkg = rf_channel_pkg.initialize()
    
    # Initialize channel configuration
    rf_pkg.init_channel(channel_cfg)
    
    print("[Simulator] MATLAB RF channel initialized")
    print(f"[Simulator] Channel config: SNR={channel_cfg['snr_db']} dB, "
          f"Doppler={channel_cfg['doppler_shift']} Hz, "
          f"Model={channel_cfg['channel_model']}")
except Exception as e:
    print(f"[Simulator] ERROR initializing MATLAB Runtime: {e}")
    import traceback
    traceback.print_exc()
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
print("=" * 60)

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
        return float(value) if isinstance(value, (int, float)) else value

# --------------------------------------------------
# Main loop
# --------------------------------------------------
packet_count = 0

while True:
    try:
        packet_bytes, addr = sock_in.recvfrom(BUFFER_SIZE)
        packet_count += 1
        print(f"\n[Simulator] ╔════════════════════════════════════╗")
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
            # Convert payload to list for MATLAB
            tx_payload = list(pkt["payload"])
            print(f"[Simulator] → Applying RF channel (MATLAB Runtime)...")
            
            # Call compiled MATLAB function
            rx_payload, metrics = rf_pkg.rf_emulator(tx_payload, nargout=2)
            
            # Convert MATLAB output back to bytes
            rx_payload_bytes = bytes([int(b) for b in rx_payload])
            
            print(f"[Simulator] ✓ RF emulation complete")
            print(f"[Simulator]   SNR: {metrics['snr_db']} dB, Doppler: {metrics['doppler']} Hz")
            
            # Show BER if available
            if 'ber' in metrics:
                ber = matlab_to_python(metrics['ber'])
                bit_errors = matlab_to_python(metrics.get('bit_errors', 0))
                bytes_total = matlab_to_python(metrics.get('bytes_total', 0))
                print(f"[Simulator]   BER: {ber:.6f} ({bit_errors}/{bytes_total*8} bits)")
            
        except Exception as e:
            print(f"[Simulator] ✗ MATLAB RF emulation failed: {e}")
            import traceback
            traceback.print_exc()
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
                rx_payload_bytes
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
        # Send metrics to analyzer
        # -----------------------------
        try:
            # Convert all MATLAB types to Python native types
            metrics_serializable = {}
            
            for key, value in metrics.items():
                metrics_serializable[key] = matlab_to_python(value)
            
            metrics_json = json.dumps(metrics_serializable)
            sock_metrics.sendto(
                metrics_json.encode(),
                (ANALYZER_HOST, ANALYZER_PORT)
            )
            print(f"[Simulator] ✓ Metrics sent to analyzer")
        except Exception as e:
            print(f"[Simulator] ✗ Metrics send failed: {e}")

        print(f"[Simulator] ╚════════════════════════════════════╝\n")

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
rf_pkg.terminate()
print("[Simulator] Stopped")