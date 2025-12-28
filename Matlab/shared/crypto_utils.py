import os

KEY = b"simurf-secret-key"

def _xor(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def encrypt(data: bytes) -> bytes:
    nonce = os.urandom(4)
    keystream = nonce + KEY
    cipher = _xor(data, keystream)
    return nonce + cipher

def decrypt(data: bytes) -> bytes:
    nonce = data[:4]
    cipher = data[4:]
    keystream = nonce + KEY
    return _xor(cipher, keystream)
