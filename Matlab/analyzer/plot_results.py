import csv
import matplotlib.pyplot as plt

packets = []
per = []
ber = []
latency = []

with open("metrics.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        packets.append(int(row["packets"]))
        per.append(float(row["PER"]))
        ber.append(float(row["BER"]))
        latency.append(float(row["avg_latency"]))

# PER plot
plt.figure()
plt.plot(packets, per, marker="o")
plt.xlabel("Packets received")
plt.ylabel("Packet Error Rate")
plt.title("PER over Time")
plt.grid(True)
plt.show()

# BER plot
plt.figure()
plt.semilogy(packets, ber, marker="o")
plt.xlabel("Packets received")
plt.ylabel("Bit Error Rate")
plt.title("BER over Time")
plt.grid(True, which="both")
plt.show()

# Latency plot
plt.figure()
plt.plot(packets, latency, marker="o")
plt.xlabel("Packets received")
plt.ylabel("Latency (s)")
plt.title("Average Latency")
plt.grid(True)
plt.show()
