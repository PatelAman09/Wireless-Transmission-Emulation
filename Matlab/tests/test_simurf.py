#!/usr/bin/env python3
"""
SimURF Test Suite
Comprehensive tests for all components.
"""
import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.packet_format import pack, unpack, Packet, calculate_overhead
from shared.crypto_utils import encrypt, decrypt, CryptoManager
from shared.fec_utils import fec_encode, fec_decode, FECCodec
from shared.metrics import MetricsCollector, PacketMetrics, PerformanceMonitor


class TestPacketFormat(unittest.TestCase):
    """Test packet serialization and validation."""
    
    def test_pack_unpack_roundtrip(self):
        """Test packing and unpacking."""
        payload = b"Hello, World!"
        packet_bytes = pack(
            seq=42,
            src_ip="192.168.1.1",
            dst_ip="192.168.1.2",
            timestamp_ns=1234567890,
            payload=payload
        )
        
        result = unpack(packet_bytes)
        
        self.assertEqual(result['seq'], 42)
        self.assertEqual(result['src_ip'], "192.168.1.1")
        self.assertEqual(result['dst_ip'], "192.168.1.2")
        self.assertEqual(result['timestamp_ns'], 1234567890)
        self.assertEqual(result['payload'], payload)
    
    def test_crc_validation(self):
        """Test CRC detects corruption."""
        payload = b"Test data"
        packet_bytes = bytearray(pack(
            seq=1,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            timestamp_ns=0,
            payload=payload
        ))
        
        # Corrupt payload
        packet_bytes[-1] ^= 0xFF
        
        with self.assertRaises(ValueError):
            unpack(bytes(packet_bytes))
    
    def test_invalid_ip_address(self):
        """Test invalid IP handling."""
        with self.assertRaises(ValueError):
            pack(
                seq=1,
                src_ip="invalid.ip",
                dst_ip="10.0.0.1",
                timestamp_ns=0,
                payload=b"data"
            )
    
    def test_calculate_overhead(self):
        """Test overhead calculation."""
        total, pct = calculate_overhead(100)
        self.assertGreater(total, 100)
        self.assertGreater(pct, 0)


class TestCrypto(unittest.TestCase):
    """Test encryption and decryption."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption/decryption."""
        plaintext = b"Secret message"
        ciphertext = encrypt(plaintext)
        decrypted = decrypt(ciphertext)
        
        self.assertEqual(plaintext, decrypted)
        self.assertNotEqual(plaintext, ciphertext)
    
    def test_different_nonces(self):
        """Test that encryption uses random nonces."""
        plaintext = b"Same message"
        cipher1 = encrypt(plaintext)
        cipher2 = encrypt(plaintext)
        
        # Should have different nonces
        self.assertNotEqual(cipher1[:4], cipher2[:4])
    
    def test_crypto_manager(self):
        """Test CryptoManager class."""
        manager = CryptoManager(key=b"test-key-12345")
        plaintext = b"Test data"
        
        ciphertext = manager.encrypt(plaintext)
        decrypted = manager.decrypt(ciphertext)
        
        self.assertEqual(plaintext, decrypted)
    
    def test_invalid_data(self):
        """Test decryption of invalid data."""
        with self.assertRaises(ValueError):
            decrypt(b"abc")  # Only 3 bytes, needs at least 5


class TestFEC(unittest.TestCase):
    """Test forward error correction."""
    
    def test_fec_encode_decode(self):
        """Test FEC encoding/decoding."""
        data = b"Test data for FEC"
        encoded = fec_encode(data, repeat=3)
        decoded = fec_decode(encoded, repeat=3)
        
        self.assertEqual(data, decoded)
        self.assertEqual(len(encoded), len(data) * 3)
    
    def test_error_correction(self):
        """Test that FEC corrects single errors."""
        codec = FECCodec(repetition=3)
        data = b"ABC"
        encoded = bytearray(codec.encode(data))
        
        # Introduce single error per byte
        encoded[0] ^= 0xFF  # Corrupt first byte of first triplet
        encoded[4] ^= 0xFF  # Corrupt middle byte of second triplet
        encoded[8] ^= 0xFF  # Corrupt last byte of third triplet
        
        decoded, corrections = codec.decode(bytes(encoded))
        
        # Should still recover original data
        self.assertEqual(decoded, data)
        self.assertEqual(corrections, 3)
    
    def test_invalid_length(self):
        """Test invalid encoded data length."""
        with self.assertRaises(ValueError):
            fec_decode(b"invalid_len", repeat=3)


class TestMetrics(unittest.TestCase):
    """Test metrics collection."""
    
    def test_metrics_collector(self):
        """Test metrics collection and aggregation."""
        collector = MetricsCollector(window_size=10)
        
        # Add some metrics
        for i in range(20):
            metrics = PacketMetrics(
                seq=i,
                timestamp_ns=i * 1000000,
                size_bytes=100,
                ber=0.001 * (i % 5),
                latency_ms=10.0 + i
            )
            collector.add_packet(metrics)
        
        summary = collector.get_summary()
        
        self.assertEqual(summary['total_packets'], 20)
        self.assertEqual(summary['window_packets'], 10)  # Limited by window
        self.assertIn('ber', summary)
        self.assertIn('latency_ms', summary)
    
    def test_performance_monitor(self):
        """Test performance monitoring."""
        monitor = PerformanceMonitor(update_interval=0.1)
        
        # Add packets
        import time
        for _ in range(10):
            monitor.update(100)
            time.sleep(0.01)
        
        time.sleep(0.1)
        stats = monitor.update(100)
        
        # Should get stats after interval
        self.assertIsNotNone(stats)
        self.assertIn('pps', stats)
        self.assertIn('kbps', stats)


class TestIntegration(unittest.TestCase):
    """Integration tests for full workflow."""
    
    def test_full_packet_pipeline(self):
        """Test complete packet processing pipeline."""
        # Original message
        message = "Integration test message"
        
        # Sender side
        plaintext = message.encode()
        ciphertext = encrypt(plaintext)
        encoded = fec_encode(ciphertext, repeat=3)
        
        packet_bytes = pack(
            seq=99,
            src_ip="10.0.0.2",
            dst_ip="10.0.0.1",
            timestamp_ns=1234567890,
            payload=encoded
        )
        
        # Simulate transmission (no corruption)
        
        # Receiver side
        pkt = unpack(packet_bytes)
        decoded = fec_decode(pkt['payload'], repeat=3)
        decrypted = decrypt(decoded)
        received_message = decrypted.decode()
        
        self.assertEqual(message, received_message)
    
    def test_pipeline_with_errors(self):
        """Test pipeline with simulated bit errors."""
        message = "Error correction test"
        
        # Encode
        plaintext = message.encode()
        ciphertext = encrypt(plaintext)
        encoded = fec_encode(ciphertext, repeat=5)  # Higher repetition
        
        packet_bytes = pack(
            seq=1,
            src_ip="10.0.0.1",
            dst_ip="10.0.0.2",
            timestamp_ns=0,
            payload=encoded
        )
        
        # Simulate errors in payload (but not header/CRC)
        pkt = unpack(packet_bytes)
        corrupted_payload = bytearray(pkt['payload'])
        
        # Introduce errors (but keep majority correct for FEC)
        for i in range(0, len(corrupted_payload), 5):
            if i < len(corrupted_payload):
                corrupted_payload[i] ^= 0xFF
        
        # Try to decode
        decoded = fec_decode(bytes(corrupted_payload), repeat=5)
        decrypted = decrypt(decoded)
        received_message = decrypted.decode()
        
        # Should still recover message with FEC
        self.assertEqual(message, received_message)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())