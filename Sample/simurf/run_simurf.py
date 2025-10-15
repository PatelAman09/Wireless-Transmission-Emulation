import numpy as np
from channel.modulation import bpsk_modulate
from channel.channel_modulation import awgn, rayleigh_fading
from channel.demodulation import bpsk_demodulate
import matplotlib.pyplot as plt


def simulate():
    # 1. Generate random bits
    n_bits = 1000
    bits = np.random.randint(0, 2, n_bits)

    # 2. Modulate (BPSK)
    tx_signal = bpsk_modulate(bits)

    # 3. Channel (add Rayleigh + AWGN) - CORRECTED
    faded_signal = rayleigh_fading(tx_signal)
    rx_signal = awgn(faded_signal, snr_db=10)  # Fixed: apply AWGN to faded signal

    # 4. Demodulate
    rx_bits = bpsk_demodulate(rx_signal)

    # 5. Evaluate
    bit_errors = np.sum(bits != rx_bits)
    ber = bit_errors / n_bits

    print(f"BER: {ber:.4f} (Errors: {bit_errors} of {n_bits})")

    # Optional: plot constellation
    plt.figure(figsize=(10, 4))

    plt.subplot(1, 2, 1)
    plt.scatter(np.real(tx_signal), np.imag(tx_signal), alpha=0.5, label='TX')
    plt.title("Transmitted Signal")
    plt.grid()
    plt.xlabel("In-Phase")
    plt.ylabel("Quadrature")
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.scatter(np.real(rx_signal), np.imag(rx_signal), alpha=0.5, label='RX', color='red')
    plt.title("Received Signal (after Rayleigh + AWGN)")
    plt.grid()
    plt.xlabel("In-Phase")
    plt.ylabel("Quadrature")
    plt.legend()

    plt.tight_layout()
    plt.savefig("constellation.png")
    plt.show()


if __name__ == "__main__":
    simulate()
