import struct
import socket
import zlib

# Network byte order (big endian)
# seq (4) | src_ip (4) | dst_ip (4) | timestamp (8) | length (2) | crc32 (4)
FMT = "!I4s4sQHI"
HEADER_SIZE = struct.calcsize(FMT)


def pack(
    seq: int,
    src_ip: str,
    dst_ip: str,
    timestamp_ns: int,
    payload: bytes
) -> bytes:
    """
    Serialize packet with CRC32 checksum.
    """
    payload_len = len(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF

    header = struct.pack(
        FMT,
        seq,
        socket.inet_aton(src_ip),
        socket.inet_aton(dst_ip),
        timestamp_ns,
        payload_len,
        crc
    )

    return header + payload


def unpack(data: bytes) -> dict:
    """
    Deserialize packet and validate checksum.
    Raises ValueError if corruption is detected.
    """
    if len(data) < HEADER_SIZE:
        raise ValueError("Packet too short")

    seq, src, dst, ts, length, recv_crc = struct.unpack(
        FMT, data[:HEADER_SIZE]
    )

    if HEADER_SIZE + length > len(data):
        raise ValueError("Corrupted length field")

    payload = data[HEADER_SIZE:HEADER_SIZE + length]

    calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if calc_crc != recv_crc:
        raise ValueError("CRC mismatch (packet corrupted)")

    return {
        "seq": seq,
        "src_ip": socket.inet_ntoa(src),
        "dst_ip": socket.inet_ntoa(dst),
        "timestamp_ns": ts,
        "payload": payload
    }
