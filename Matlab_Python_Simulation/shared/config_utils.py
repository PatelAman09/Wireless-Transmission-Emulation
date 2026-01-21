import os
import json


def load_simurf_config():
    base_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    config_path = os.path.join(
        base_dir, "config", "matlab_channel_config.json"
    )

    with open(config_path) as f:
        return json.load(f)
