import socket

ETH_HEADER_LEN = 14

def capture_packet(interface="eth0", max_size=1600):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    s.bind((interface, 0))

    raw_packet, _ = s.recvfrom(max_size)

    payload = raw_packet[ETH_HEADER_LEN:]
    return payload, raw_packet
