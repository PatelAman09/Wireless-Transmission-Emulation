"""
Configuration loading and validation utilities.
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class SimURFConfig:
    """SimURF configuration manager."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_dir: Path to config directory (auto-detected if None)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Auto-detect config directory
            current = Path(__file__).parent
            self.config_dir = current.parent / "config"
        
        if not self.config_dir.exists():
            raise ConfigurationError(f"Config directory not found: {self.config_dir}")
    
    def load_matlab_channel_config(self) -> Dict[str, Any]:
        """
        Load MATLAB channel configuration.
        
        Returns:
            Configuration dictionary
        """
        config_path = self.config_dir / "matlab_channel_config.json"
        return self._load_json(config_path, self._validate_channel_config)
    
    def load_network_config(self) -> Dict[str, Any]:
        """
        Load network configuration.
        
        Returns:
            Configuration dictionary
        """
        config_path = self.config_dir / "network_config.json"
        return self._load_json(config_path, self._validate_network_config)
    
    def load_test_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Load test scenario configuration.
        
        Args:
            scenario_name: Name of scenario file (without .json)
            
        Returns:
            Scenario configuration
        """
        config_path = self.config_dir / "scenarios" / f"{scenario_name}.json"
        return self._load_json(config_path)
    
    def _load_json(self, path: Path, validator=None) -> Dict[str, Any]:
        """Load and validate JSON configuration file."""
        try:
            with open(path) as f:
                config = json.load(f)
            
            if validator:
                validator(config)
            
            return config
        except FileNotFoundError:
            raise ConfigurationError(f"Config file not found: {path}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {path}: {e}")
    
    @staticmethod
    def _validate_channel_config(config: Dict[str, Any]):
        """Validate channel configuration."""
        required = ["snr_db", "sample_rate", "channel_model"]
        for field in required:
            if field not in config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        # Validate SNR range
        snr = config["snr_db"]
        if not -20 <= snr <= 60:
            raise ConfigurationError(f"SNR {snr} dB out of range [-20, 60]")
        
        # Validate sample rate
        sr = config["sample_rate"]
        if sr <= 0:
            raise ConfigurationError(f"Invalid sample rate: {sr}")
    
    @staticmethod
    def _validate_network_config(config: Dict[str, Any]):
        """Validate network configuration."""
        required = ["mode", "listen", "forward"]
        for field in required:
            if field not in config:
                raise ConfigurationError(f"Missing required field: {field}")
        
        # Validate mode
        if config["mode"] not in ["udp", "tcp"]:
            raise ConfigurationError(f"Invalid mode: {config['mode']}")


# Backward compatibility function
def load_simurf_config() -> Dict[str, Any]:
    """
    Load SimURF channel configuration.
    
    Returns:
        Configuration dictionary
    """
    manager = SimURFConfig()
    return manager.load_matlab_channel_config()


def get_config_value(key: str, default: Any = None) -> Any:
    """
    Get a specific configuration value.
    
    Args:
        key: Configuration key (supports dot notation, e.g., "impairments.enable")
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    manager = SimURFConfig()
    
    try:
        # Try channel config first
        config = manager.load_matlab_channel_config()
    except ConfigurationError:
        try:
            # Fall back to network config
            config = manager.load_network_config()
        except ConfigurationError:
            return default
    
    # Support dot notation
    keys = key.split(".")
    value = config
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default
    
    return value