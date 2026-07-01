"""
Configuration Loader for Spatiotemporal Heterogeneity Model

Loads YAML configuration files and converts them to EasyDict objects
for convenient dot-notation access (e.g., config.crash_probability.wind.k_w)
"""

import yaml
from pathlib import Path
from typing import Optional, Union


def _convert_to_easy_dict(data: dict):
    """
    Recursively convert nested dictionaries to support dot notation access.
    
    Args:
        data: Dictionary to convert
        
    Returns:
        Object with dot notation access to nested keys
    """
    if isinstance(data, EasyDict):
        # Already converted, recurse into children only
        return EasyDict({key: _convert_to_easy_dict(value) for key, value in data.items()})
    elif isinstance(data, dict):
        return EasyDict({key: _convert_to_easy_dict(value) for key, value in data.items()})
    elif isinstance(data, list):
        return [_convert_to_easy_dict(item) for item in data]
    else:
        return data


class EasyDict(dict):
    """
    A dictionary subclass that allows attribute-style access.
    
    Example:
        >>> config = EasyDict({'a': {'b': 1}})
        >>> config.a.b  # Returns 1
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self
    
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")
    
    def __setattr__(self, key, value):
        self[key] = value
    
    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{key}'")


def load_config(config_path: Optional[Union[str, Path]] = None) -> EasyDict:
    """
    Load configuration from YAML file and return as EasyDict.
    
    Args:
        config_path: Path to YAML configuration file. 
                    If None, defaults to common.yaml in configs directory.
    
    Returns:
        EasyDict object with dot notation access to configuration parameters
    
    Example:
        >>> config = load_config()
        >>> print(config.crash_probability.wind.k_w)  # 3.0
        >>> print(config.population_tidal.sigma_decay.micro)  # 60.0
    """
    if config_path is None:
        # Default path: methods/spatiotemporal_heterogeneity/configs/common.yaml
        config_path = Path(__file__).parent.parent.parent / "configs" / "common.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_data = yaml.safe_load(f)
    
    return _convert_to_easy_dict(config_data)


def load_all_configs(config_dir: Optional[Union[str, Path]] = None) -> dict:
    """
    Load all YAML configuration files from a directory.
    
    Args:
        config_dir: Directory containing YAML config files.
                   If None, defaults to configs directory.
    
    Returns:
        Dictionary mapping config file names (without extension) to EasyDict objects
    
    Example:
        >>> configs = load_all_configs()
        >>> risk_config = configs['risk_params']
        >>> env_config = configs['env_config']
    """
    if config_dir is None:
        config_dir = Path(__file__).parent.parent.parent / "configs"
    
    config_dir = Path(config_dir)
    
    if not config_dir.exists():
        raise FileNotFoundError(f"Configuration directory not found: {config_dir}")
    
    configs = {}
    for yaml_file in config_dir.glob("*.yaml"):
        config_name = yaml_file.stem
        configs[config_name] = load_config(yaml_file)
    
    return configs


# Convenience function for quick access
def get_risk_config() -> EasyDict:
    """
    Quick access to risk parameters configuration.
    
    Returns:
        EasyDict with risk parameters
    
    Example:
        >>> config = get_risk_config()
        >>> lambda_base = config.crash_probability.lambda_base
        >>> k_w = config.crash_probability.wind.k_w
    """
    return load_config()


if __name__ == "__main__":
    # Test the configuration loader
    print("=" * 60)
    print("Testing Configuration Loader")
    print("=" * 60)
    
    # Load risk parameters
    config = load_config()
    
    print("\n1. Crash Probability Parameters:")
    print(f"   lambda_base: {config.crash_probability.lambda_base}")
    print(f"   wind.V_limit: {config.crash_probability.wind.V_limit}")
    print(f"   wind.k_w: {config.crash_probability.wind.k_w}")
    print(f"   wind.theta: {config.crash_probability.wind.theta}")
    print(f"   rain.gamma_rain: {config.crash_probability.rain.gamma_rain}")
    print(f"   urban_canyon.K_obs: {config.crash_probability.urban_canyon.K_obs}")
    print(f"   urban_canyon.w_svf: {config.crash_probability.urban_canyon.w_svf}")
    
    print("\n2. Population Parameters:")
    print(f"   sigma_decay: {config.population.sigma_decay}")
    print(f"   poi_weights.office: {config.population.poi_weights.office}")
    print(f"   activation.office_peaks: {config.population.activation.office_peaks}")
    
    print("\n3. Noise Sensitivity:")
    print(f"   landuse_s.residential: {config.noise_sensitivity.landuse_s.residential}")
    print(f"   time_penalty.nighttime: {config.noise_sensitivity.time_penalty.nighttime}")
    
    print("\n4. Property Risk:")
    print(f"   log_normal_mu: {config.property_risk.log_normal_mu}")
    print(f"   max_prop_damage: {config.property_risk.max_prop_damage}")
    
    print("\n5. Fatal Risk:")
    print(f"   lethal_alpha: {config.fatal_risk.lethal_alpha}")
    print(f"   lethal_beta: {config.fatal_risk.lethal_beta}")
    
    print("\n" + "=" * 60)
    print("Configuration loaded successfully!")
    print("=" * 60)
