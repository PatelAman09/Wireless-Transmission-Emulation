# rf_channel_pkg - Compiled MATLAB Package

This package was compiled from MATLAB using MATLAB Compiler SDK.

## Installation

```bash
pip install .
```

## Requirements

- Python 3.8, 3.9, 3.10, or 3.11
- MATLAB Runtime R2025b (automatically downloaded if not present)

## Usage

```python
import rf_channel_pkg

# Initialize the package
pkg = rf_channel_pkg.initialize()

# Initialize channel
config = {
    'snr_db': 20,
    'doppler_shift': 10,
    'channel_model': 'Rayleigh'
}
pkg.init_channel(config)

# Process data
tx_data = [1, 2, 3, 4, 5]
rx_data, metrics = pkg.rf_emulator(tx_data, nargout=2)

# Cleanup
pkg.terminate()
```

## File Size Warning

This compiled package is small (~10 MB), but requires MATLAB Runtime
(~3 GB) to execute. The Runtime will be downloaded automatically
on first use if not already installed.
