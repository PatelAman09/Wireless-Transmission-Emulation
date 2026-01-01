import socket
import time
import signal
import sys

from shared.packet_format import unpack, pack
from simulator.simurf_matlab_bridge import SimuRFMatlab


LISTEN_ADDR = ("0.0.0.0", 5000)
DEST = ("127.0.0.1", 6000)


def main():
    print("[SIMULATOR] Running (Ctrl+C to stop)")

    recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    recv_sock.bind(LISTEN_ADDR)

    send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    simurf = SimuRFMatlab()

    try:
        while True:
            data, addr = recv_sock.recvfrom(4096)
            pkt = unpack(data)

            # RF metrics only
            _, metrics = simurf.simulate(b"")

            out = pack(
                pkt["seq"],
                pkt["src_ip"],
                pkt["dst_ip"],
                int(time.time() * 1e6),
                pkt["payload"]
            )

            send_sock.sendto(out, DEST)

    except KeyboardInterrupt:
        print("\n[SIMULATOR] Shutdown requested")

    finally:
        print("[SIMULATOR] Cleaning up")

        try:
            recv_sock.close()
            send_sock.close()
        except Exception:
            pass

        try:
            simurf.close()
        except Exception:
            pass

        print("[SIMULATOR] Stopped cleanly")
        sys.exit(0)


if __name__ == "__main__":
    main()
