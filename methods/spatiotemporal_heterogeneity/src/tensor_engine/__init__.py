"""
Tensor Engine for Spatiotemporal Heterogeneity Model

Provides core modules for:
- Grid system management (grid_system)
- Configuration loading (load_config, config_manager)
- Dynamic risk models (dynamic_p_crash, dynamic_population, dynamic_noise, dynamic_fatality)
- Static obstacle modeling (static_obstacle)
- Tensor assembly and normalization (tensor_builder)
"""

from .grid_system import GridSystem, SpatialGridConfig, TemporalGridConfig, get_micro_grid
from .load_config import load_config, load_all_configs, get_risk_config, EasyDict
from .config_manager import (
    ConfigManager,
    get_config_manager,
    load_micro_config,
    load_macro_config,
)
from .tensor_builder import TensorBuilder
from .dynamic_noise import DynamicNoiseCost, NoiseConfig, get_micro_grid_noise_model, get_macro_grid_noise_model
from .dynamic_fatality import DynamicFatalityModel, FatalityConfig
from .risk_tensor_assembler import build_risk_tensors

__all__ = [
    # Grid system
    'GridSystem',
    'SpatialGridConfig',
    'TemporalGridConfig',
    'get_micro_grid',
    
    # Configuration (legacy)
    'load_config',
    'load_all_configs',
    'get_risk_config',
    'EasyDict',
    
    # Configuration (new)
    'ConfigManager',
    'get_config_manager',
    'load_micro_config',
    'load_macro_config',
    
    # Tensor building
    'TensorBuilder',
    
    # Risk models
    'DynamicNoiseCost',
    'NoiseConfig',
    'get_micro_grid_noise_model',
    'get_macro_grid_noise_model',
    'DynamicFatalityModel',
    'FatalityConfig',
    'build_risk_tensors',
]
