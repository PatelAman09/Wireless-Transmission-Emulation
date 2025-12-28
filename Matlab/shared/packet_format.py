import struct
import socket

FMT = "!I4s4sQH"

def pack(seq, src, dst, ts, payload: bytes) -> bytes:
    header = struct.pack(
        FMT,
        seq,
        socket.inet_aton(src),
        socket.inet_aton(dst),
        ts,
        len(payload)
    )
    return header + payload


def unpack(data: bytes) -> dict:
    hdr_size = struct.calcsize(FMT)
    seq, src, dst, ts, length = struct.unpack(FMT, data[:hdr_size])
    payload = data[hdr_size:hdr_size + length]

    return {
        "seq": seq,
        "src_ip": socket.inet_ntoa(src),
        "dst_ip": socket.inet_ntoa(dst),
        "timestamp": ts,
        "payload": payload
    }
