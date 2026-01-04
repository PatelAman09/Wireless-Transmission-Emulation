def fec_encode(data: bytes, repeat: int = 3) -> bytes:
    """
    Simple repetition-code FEC.
    Each byte is repeated `repeat` times.
    """
    return b"".join(bytes([b]) * repeat for b in data)


def fec_decode(data: bytes, repeat: int = 3) -> bytes:
    """
    Majority-vote decoding for repetition code.
    """
    if len(data) % repeat != 0:
        raise ValueError("Invalid FEC data length")

    decoded = bytearray()

    for i in range(0, len(data), repeat):
        chunk = data[i:i + repeat]
        decoded.append(max(set(chunk), key=chunk.count))

    return bytes(decoded)
