"""
Forward Error Correction utilities.
Implements simple repetition codes and majority-vote decoding.
"""
from typing import Tuple
from collections import Counter


class FECCodec:
    """Forward Error Correction codec using repetition coding."""
    
    def __init__(self, repetition: int = 3):
        """
        Initialize FEC codec.
        
        Args:
            repetition: Number of times to repeat each byte (default: 3)
        """
        if repetition < 1 or repetition > 15:
            raise ValueError(f"Repetition must be 1-15, got {repetition}")
        self.repetition = repetition
    
    def encode(self, data: bytes) -> bytes:
        """
        Encode data with repetition code.
        
        Each byte is repeated `repetition` times.
        
        Args:
            data: Original data
            
        Returns:
            Encoded data (length = len(data) * repetition)
        """
        if not data:
            return b""
        
        return b"".join(bytes([b]) * self.repetition for b in data)
    
    def decode(self, data: bytes) -> Tuple[bytes, int]:
        """
        Decode data using majority voting.
        
        Args:
            data: Encoded data
            
        Returns:
            (decoded_data, corrections_made)
            
        Raises:
            ValueError: If data length is invalid
        """
        if len(data) % self.repetition != 0:
            raise ValueError(
                f"Invalid encoded data length: {len(data)} not divisible by {self.repetition}"
            )
        
        if not data:
            return b"", 0
        
        decoded = bytearray()
        corrections = 0
        
        for i in range(0, len(data), self.repetition):
            chunk = data[i:i + self.repetition]
            
            # Majority vote
            counter = Counter(chunk)
            majority_byte, count = counter.most_common(1)[0]
            
            decoded.append(majority_byte)
            
            # Count corrections (bytes that didn't match majority)
            corrections += (self.repetition - count)
        
        return bytes(decoded), corrections
    
    def get_overhead(self) -> float:
        """
        Calculate encoding overhead.
        
        Returns:
            Overhead factor (e.g., 3.0 for triple repetition)
        """
        return float(self.repetition)
    
    def max_correctable_errors_per_byte(self) -> int:
        """
        Maximum correctable errors per encoded byte group.
        
        Returns:
            Number of errors that can be corrected
        """
        return (self.repetition - 1) // 2


# Default codec for backward compatibility
_default_codec = FECCodec(repetition=3)


def fec_encode(data: bytes, repeat: int = 3) -> bytes:
    """
    Encode data with repetition code.
    
    Args:
        data: Data to encode
        repeat: Repetition factor
        
    Returns:
        Encoded data
    """
    codec = FECCodec(repetition=repeat)
    return codec.encode(data)


def fec_decode(data: bytes, repeat: int = 3) -> bytes:
    """
    Decode data with majority voting.
    
    Args:
        data: Encoded data
        repeat: Repetition factor
        
    Returns:
        Decoded data
        
    Raises:
        ValueError: If data length is invalid
    """
    codec = FECCodec(repetition=repeat)
    decoded, _ = codec.decode(data)
    return decoded


def fec_decode_with_stats(data: bytes, repeat: int = 3) -> Tuple[bytes, int]:
    """
    Decode data and return correction statistics.
    
    Args:
        data: Encoded data
        repeat: Repetition factor
        
    Returns:
        (decoded_data, num_corrections)
    """
    codec = FECCodec(repetition=repeat)
    return codec.decode(data)