"""
Simple XOR-based encryption for demonstration purposes.
"""
import os
import hashlib
from typing import Optional

# Default demonstration key
DEFAULT_KEY = b"simurf-secret-key-v1"


class CryptoManager:
    """Manages encryption/decryption with configurable keys."""
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize crypto manager.
        
        Args:
            key: Encryption key (default: demonstration key)
        """
        self.key = key or DEFAULT_KEY
        if len(self.key) < 8:
            raise ValueError("Key too short (minimum 8 bytes)")
    
    def _xor(self, data: bytes, keystream: bytes) -> bytes:
        """XOR data with keystream."""
        return bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(data))
    
    def encrypt(self, plaintext: bytes) -> bytes:
        """
        Encrypt data with random nonce.
        
        Format: [4-byte nonce][encrypted data]
        
        Args:
            plaintext: Data to encrypt
            
        Returns:
            Encrypted data with prepended nonce
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty data")
            
        # Generate random nonce
        nonce = os.urandom(4)
        
        # Create keystream from nonce + key
        keystream = nonce + self.key
        
        # Encrypt
        ciphertext = self._xor(plaintext, keystream)
        
        return nonce + ciphertext
    
    def decrypt(self, data: bytes) -> bytes:
        """
        Decrypt data.
        
        Args:
            data: Encrypted data with nonce
            
        Returns:
            Decrypted plaintext
            
        Raises:
            ValueError: If data is too short or invalid
        """
        if len(data) < 5:  # At least 4-byte nonce + 1 byte data
            raise ValueError(f"Data too short for decryption: {len(data)} bytes")
        
        # Extract nonce
        nonce = data[:4]
        ciphertext = data[4:]
        
        # Recreate keystream
        keystream = nonce + self.key
        
        # Decrypt
        plaintext = self._xor(ciphertext, keystream)
        
        return plaintext
    
    @staticmethod
    def generate_key(seed: Optional[str] = None) -> bytes:
        """
        Generate a deterministic key from seed.
        
        Args:
            seed: Optional seed string (uses random if None)
            
        Returns:
            32-byte key
        """
        if seed:
            return hashlib.sha256(seed.encode()).digest()
        else:
            return os.urandom(32)


# Global default instance for backward compatibility
_default_manager = CryptoManager()


def encrypt(data: bytes) -> bytes:
    """Encrypt using default manager."""
    return _default_manager.encrypt(data)


def decrypt(data: bytes) -> bytes:
    """Decrypt using default manager."""
    return _default_manager.decrypt(data)