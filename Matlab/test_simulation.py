#!/usr/bin/env python3
import time
import socket
from scapy.all import IP, UDP, TCP, ICMP, Raw, send
import threading

def test_basic_packets():
    """Send test packets to see SimuRF processing"""
    print("🚀 Starting SimuRF Test...")
    print("📡 Send test packets and check container logs")
    
    test_packets = [
        {"type": "ICMP", "data": "PING_TEST_1", "size": 64},
        {"type": "UDP", "data": "UDP_TEST_PACKET", "size": 128},
        {"type": "TCP", "data": "TCP_STREAM_TEST", "size": 256},
        {"type": "ICMP", "data": "PING_TEST_2", "size": 84},
    ]
    
    for i, packet_info in enumerate(test_packets):
        print(f"\n📤 Sending test packet {i+1}: {packet_info['type']} ({packet_info['size']} bytes)")
        
        if packet_info['type'] == "ICMP":
            packet = IP(dst="8.8.8.8")/ICMP()/Raw(load=packet_info['data'].encode())
        elif packet_info['type'] == "UDP":
            packet = IP(dst="8.8.8.8")/UDP(sport=12345, dport=54321)/Raw(load=packet_info['data'].encode())
        elif packet_info['type'] == "TCP":
            packet = IP(dst="8.8.8.8")/TCP(sport=12345, dport=80)/Raw(load=packet_info['data'].encode())
        
        send(packet, verbose=0)
        time.sleep(2)  # Wait between packets
    
    print("\n✅ All test packets sent! Check SimuRF container logs.")

def continuous_traffic():
    """Generate continuous traffic for testing"""
    print("🔄 Generating continuous traffic...")
    counter = 0
    try:
        while True:
            packet = IP(dst="8.8.8.8")/ICMP()/Raw(load=f"Continuous_test_{counter}".encode())
            send(packet, verbose=0)
            print(f"📤 Sent continuous packet {counter}")
            counter += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopped continuous traffic")

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Basic test packets")
    print("2. Continuous traffic")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        test_basic_packets()
    elif choice == "2":
        continuous_traffic()
    else:
        test_basic_packets()