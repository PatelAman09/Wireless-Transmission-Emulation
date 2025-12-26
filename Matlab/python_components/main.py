import os
from packet_capture import capture_packet
from packet_forward import forward_packet
from simurf_matlab_bridge import SimuRFMatlab
from config_loader import load_config

# ---------- Path handling (robust) ----------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NET_CFG = os.path.join(BASE_DIR, "config", "network_config.json")
MAT_CFG = os.path.join(BASE_DIR, "config", "matlab_channel_config.json")

# ---------- Packet filters ----------
def is_ipv4_udp(packet: bytes) -> bool:
    """
    Ethernet + IPv4 + UDP filter
    """
    # Ethernet type
    if packet[12:14] != b"\x08\x00":  # IPv4
        return False

    # IP protocol field
    ip_proto = packet[23]
    return ip_proto == 17  # UDP


def is_loop_packet(packet: bytes) -> bool:
    """
    Prevent forwarding loops when using same interface
    """
    dst_mac = packet[0:6]
    src_mac = packet[6:12]
    return src_mac == dst_mac


# ---------- Main ----------
def main():
    net_cfg = load_config(NET_CFG)

    simurf = SimuRFMatlab(MAT_CFG)

    print("[SimuRF] Mode A - Transparent RF Emulation Started")
    print("[SimuRF] Waiting for packets...")

    pkt_count = 0

    while True:
        payload, raw_packet = capture_packet(
            net_cfg["input_interface"],
            net_cfg.get("max_packet_size", 1500)
        )

        if payload is None:
            continue

        # Filter non-UDP traffic
        if not is_ipv4_udp(raw_packet):
            continue

        # Prevent infinite forwarding loop
        if is_loop_packet(raw_packet):
            continue

        pkt_count += 1

        # MATLAB RF simulation (Mode A)
        iq_samples, channel_info = simurf.simulate(payload)

        ber = channel_info["ber"]
        evm = channel_info["evm"]
        snr = channel_info["snr_db"]
        channel = channel_info["channel_model"]

        # LIVE SIMULATION FEEDBACK
        print(
            f"[PKT {pkt_count}] "
            f"Channel={channel} | "
            f"SNR={snr} dB | "
            f"BER={ber:.2e} | "
            f"EVM={evm:.3f} | "
            f"IQ Samples={len(iq_samples)}"
        )

        # Forward packet unchanged (Mode A)
        forward_packet(raw_packet, net_cfg["output_interface"])


if __name__ == "__main__":
    main()
