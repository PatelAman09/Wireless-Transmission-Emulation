import socket

def forward_packet(raw_packet, interface="eth1"):
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
    s.bind((interface, 0))
    s.send(raw_packet)
