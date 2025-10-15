import numpy as np


def bpsk_demodulate(received_signal):
    return (np.real(received_signal) > 0).astype(int)
