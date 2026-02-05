"""
Packet format with robust CRC32 validation and serialization.
"""
import struct
import socket
import zlib
from typing import Dict, Tuple
from dataclasses import dataclass

# Network byte order (big endian)
# Format: seq (4) | src_ip (4) | dst_ip (4) | timestamp (8) | length (2) | crc32 (4)
HEADER_FORMAT = "!I4s4sQHI"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# Constants
MAX_PAYLOAD_SIZE = 65507  # Max UDP payload (65535 - 8 UDP header - 20 IP header)
MIN_PACKET_SIZE = HEADER_SIZE


@dataclass
class Packet:
    """Structured packet representation."""
    seq: int
    src_ip: str
    dst_ip: str
    timestamp_ns: int
    payload: bytes
    
    def __post_init__(self):
        """Validate packet fields."""
        if not 0 <= self.seq <= 0xFFFFFFFF:
            raise ValueError(f"Sequence number {self.seq} out of range")
        if len(self.payload) > MAX_PAYLOAD_SIZE:
            raise ValueError(f"Payload too large: {len(self.payload)} > {MAX_PAYLOAD_SIZE}")


def pack(seq: int, src_ip: str, dst_ip: str, timestamp_ns: int, payload: bytes) -> bytes:
    """
    Serialize packet with CRC32 checksum.
    
    Args:
        seq: Sequence number (0-4294967295)
        src_ip: Source IP address string (e.g., "10.0.0.2")
        dst_ip: Destination IP address string
        timestamp_ns: Timestamp in nanoseconds
        payload: Data bytes to transmit
        
    Returns:
        Serialized packet bytes
        
    Raises:
        ValueError: If parameters are invalid
    """
    # Validate inputs
    pkt = Packet(seq, src_ip, dst_ip, timestamp_ns, payload)
    
    payload_len = len(payload)
    crc = zlib.crc32(payload) & 0xFFFFFFFF

    try:
        header = struct.pack(
            HEADER_FORMAT,
            seq,
            socket.inet_aton(src_ip),
            socket.inet_aton(dst_ip),
            timestamp_ns,
            payload_len,
            crc
        )
    except socket.error as e:
        raise ValueError(f"Invalid IP address: {e}")

    return header + payload


def unpack(data: bytes) -> Dict[str, any]:
    """
    Deserialize packet and validate checksum.
    
    Args:
        data: Raw packet bytes
        
    Returns:
        Dictionary with packet fields:
            - seq: Sequence number
            - src_ip: Source IP string
            - dst_ip: Destination IP string
            - timestamp_ns: Timestamp in nanoseconds
            - payload: Payload bytes
            
    Raises:
        ValueError: If packet is corrupted or invalid
    """
    if len(data) < HEADER_SIZE:
        raise ValueError(f"Packet too short: {len(data)} < {HEADER_SIZE}")

    try:
        seq, src, dst, ts, length, recv_crc = struct.unpack(
            HEADER_FORMAT, data[:HEADER_SIZE]
        )
    except struct.error as e:
        raise ValueError(f"Header unpack failed: {e}")

    expected_total = HEADER_SIZE + length
    if expected_total > len(data):
        raise ValueError(
            f"Corrupted length field: expected {expected_total}, got {len(data)}"
        )

    payload = data[HEADER_SIZE:HEADER_SIZE + length]

    # Verify CRC
    calc_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if calc_crc != recv_crc:
        raise ValueError(
            f"CRC mismatch: calculated {calc_crc:08x}, received {recv_crc:08x}"
        )

    return {
        "seq": seq,
        "src_ip": socket.inet_ntoa(src),
        "dst_ip": socket.inet_ntoa(dst),
        "timestamp_ns": ts,
        "payload": payload
    }


def calculate_overhead(payload_size: int) -> Tuple[int, float]:
    """
    Calculate packet overhead for given payload size.
    
    Returns:
        (total_packet_size, overhead_percentage)
    """
    total = HEADER_SIZE + payload_size
    overhead_pct = (HEADER_SIZE / total) * 100 if total > 0 else 0
    return total, overhead_pct