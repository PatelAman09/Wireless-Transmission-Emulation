#!/usr/bin/env python3
"""
Test the complete encryption → FEC → RF → FEC decode → decryption pipeline
"""

import sys
import os

# Add shared modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.crypto_utils import encrypt, decrypt
from shared.fec_utils import fec_encode, fec_decode

def introduce_bit_errors(data, error_rate=0.02):
    """Simulate RF channel bit errors"""
    import random
    result = bytearray(data)
    num_bits = len(data) * 8
    num_errors = int(num_bits * error_rate)
    
    for _ in range(num_errors):
        byte_idx = random.randint(0, len(result) - 1)
        bit_idx = random.randint(0, 7)
        result[byte_idx] ^= (1 << bit_idx)  # Flip bit
    
    return bytes(result)

def test_pipeline(message, error_rate=0.02):
    """Test complete pipeline"""
    print(f"\n{'='*60}")
    print(f"Testing: '{message}' (BER={error_rate})")
    print(f"{'='*60}")
    
    # Step 1: Encrypt
    plaintext = message.encode()
    ciphertext = encrypt(plaintext)
    print(f"1. Encrypted: {len(plaintext)} → {len(ciphertext)} bytes")
    
    # Step 2: FEC encode
    fec_encoded = fec_encode(ciphertext, repeat=3)
    print(f"2. FEC encoded: {len(ciphertext)} → {len(fec_encoded)} bytes (3x)")
    
    # Step 3: Simulate RF channel errors
    corrupted = introduce_bit_errors(fec_encoded, error_rate)
    bit_errors = sum(bin(a ^ b).count('1') for a, b in zip(fec_encoded, corrupted))
    actual_ber = bit_errors / (len(fec_encoded) * 8)
    print(f"3. RF channel: {bit_errors} bit errors (BER={actual_ber:.4f})")
    
    # Step 4: FEC decode
    try:
        fec_decoded = fec_decode(corrupted, repeat=3)
        corrected_errors = sum(a != b for a, b in zip(ciphertext, fec_decoded))
        print(f"4. FEC decoded: {len(fec_decoded)} bytes, {corrected_errors} byte errors remaining")
    except Exception as e:
        print(f"4. FEC decode FAILED: {e}")
        return False
    
    # Step 5: Decrypt
    try:
        decrypted = decrypt(fec_decoded)
        recovered = decrypted.decode(errors='replace')
        print(f"5. Decrypted: '{recovered}'")
        
        if recovered == message:
            print("✅ SUCCESS: Message recovered perfectly!")
            return True
        else:
            print(f"⚠️  PARTIAL: Message corrupted")
            print(f"   Expected: '{message}'")
            print(f"   Got:      '{recovered}'")
            return False
    except Exception as e:
        print(f"5. Decrypt FAILED: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing Encryption → FEC → RF → FEC Decode → Decryption")
    print("="*60)
    
    test_cases = [
        ("Hello", 0.02),
        ("Wireless", 0.02),
        ("SimURF Demo", 0.02),
        ("Hello World!", 0.05),  # Higher error rate
        ("Test message with more text", 0.02),
    ]
    
    results = []
    for msg, ber in test_cases:
        success = test_pipeline(msg, ber)
        results.append((msg, success))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    passed = sum(1 for _, s in results if s)
    total = len(results)
    
    for msg, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: '{msg}'")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n✅ All tests passed! Pipeline working correctly.")
        print("The issue is likely in the MATLAB RF emulator.")
    else:
        print(f"\n⚠️  {total - passed} tests failed.")
        print("FEC may not be correcting enough errors.")