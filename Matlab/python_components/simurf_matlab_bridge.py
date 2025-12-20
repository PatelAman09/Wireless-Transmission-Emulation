import matlab.engine
import numpy as np
import time
import os

class SimuRFMatlab:
    def __init__(self, config_path):
        """
        Starts MATLAB engine and prepares RF simulation environment
        """
        print("[SimuRF] Launching MATLAB engine (this may take up to 1 minute)...")
        start_time = time.time()

        self.eng = matlab.engine.start_matlab()

        elapsed = time.time() - start_time
        print(f"[SimuRF] MATLAB engine started in {elapsed:.1f} seconds")

        # Add MATLAB source folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        matlab_dir = os.path.join(base_dir, "matlab_components")

        self.eng.addpath(matlab_dir, nargout=0)

        self.config_path = config_path

    def simulate(self, payload_bytes: bytes):
        """
        Run Mode-A RF simulation in MATLAB
        """
        matlab_bytes = matlab.uint8(list(payload_bytes))

        complex_samples, channel_info = self.eng.professional_rf_emulator(
            matlab_bytes,
            self.config_path,
            nargout=2
        )

        iq = np.array(complex_samples, dtype=np.complex64)
        return iq, channel_info

    def close(self):
        """
        Cleanly shut down MATLAB engine
        """
        self.eng.quit()
