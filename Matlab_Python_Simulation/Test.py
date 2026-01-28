import numpy as np
import rf_channel_pkg

print("Initializing MATLAB Runtime...")
pkg = rf_channel_pkg.initialize()
print("✓ Initialized!")

config = {
    'snr_db': 20.0,
    'doppler_shift': 10.0,
    'channel_model': 'Rayleigh'
}
pkg.init_channel(config, nargout=0)
print("✓ Channel initialized!")

tx_data = np.array([72, 101, 108, 108, 111], dtype=np.uint8)
rx_data, metrics = pkg.rf_emulator(tx_data, nargout=2)

print("✓ RF emulation works!")
print("Metrics:", metrics)

pkg.terminate()
print("✓ Test complete!")
