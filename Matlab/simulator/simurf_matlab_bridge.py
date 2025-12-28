from pathlib import Path
import matlab.engine

class SimuRFMatlab:
    def __init__(self):
        print("[MATLAB] Starting MATLAB engine...")
        self.eng = matlab.engine.start_matlab()

        project_root = Path(__file__).resolve().parents[1]
        self.eng.addpath(str(project_root / "matlab_components"), nargout=0)

        self.cfg_path = str(project_root / "config" / "matlab_channel_config.json")
        print("[MATLAB] Engine ready")

    def simulate(self, payload):
        rx_bits, metrics = self.eng.professional_rf_emulator(
            payload,
            self.cfg_path,
            nargout=2
        )
        return rx_bits, metrics
