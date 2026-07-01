"""
Base Risk Model - Abstract Interface for All Risk Types

Defines the common interface that all risk models must implement.
This ensures consistency and enables modular risk computation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import numpy as np
from pathlib import Path


class BaseRiskModel(ABC):
    """Abstract base class for all risk models.
    
    All risk models must inherit from this class and implement:
    - compute_risk(): Main computation method
    - get_default_parameters(): Default parameter values
    - validate_parameters(): Parameter validation
    
    This design enables:
    - Consistent interface across all risk types
    - Easy testing of individual risks
    - Plug-and-play risk model composition
    """
    
    def __init__(self, name: str, parameters: Dict[str, Any] = None):
        """
        Args:
            name: Risk model name (e.g., 'fatality', 'property', 'noise')
            parameters: Risk-specific parameters (uses defaults if None)
        """
        self.name = name
        self.parameters = parameters or self.get_default_parameters()
        self.validate_parameters()
    
    @abstractmethod
    def compute_risk(
        self,
        grid,
        data: Dict[str, Any],
        **kwargs
    ) -> np.ndarray:
        """Compute risk map for this risk type.
        
        Args:
            grid: Grid3D object containing airspace grid
            data: Dictionary containing required data layers
                  (e.g., population, buildings, etc.)
            **kwargs: Additional risk-specific parameters
        
        Returns:
            2D numpy array (height, width) with risk values per cell
            OR 3D array (layers, height, width) if altitude-dependent
        """
        pass
    
    @abstractmethod
    def get_default_parameters(self) -> Dict[str, Any]:
        """Return default parameters for this risk model.
        
        Returns:
            Dictionary of parameter name -> default value
        """
        pass
    
    def validate_parameters(self) -> bool:
        """Validate that all required parameters are present and valid.
        
        Returns:
            True if valid
            
        Raises:
            ValueError: If parameters are invalid
        """
        # Default validation - override if needed
        return True
    
    def get_risk_statistics(self, risk_map: np.ndarray) -> Dict[str, float]:
        """Compute statistical summary of risk map.
        
        Args:
            risk_map: Risk array from compute_risk()
            
        Returns:
            Dictionary with min, max, mean, std, etc.
        """
        return {
            'min': float(risk_map.min()),
            'max': float(risk_map.max()),
            'mean': float(risk_map.mean()),
            'std': float(risk_map.std()),
            'median': float(np.median(risk_map)),
            'total': float(risk_map.sum()),
            'non_zero_count': int(np.count_nonzero(risk_map)),
        }
    
    def normalize_risk(
        self,
        risk_map: np.ndarray,
        method: str = 'minmax'
    ) -> np.ndarray:
        """Normalize risk map to [0, 1] range.
        
        Args:
            risk_map: Risk array
            method: Normalization method
                   - 'minmax': Scale to [0, 1]
                   - 'zscore': Z-score normalization
                   - 'log': Log normalization
        
        Returns:
            Normalized risk array
        """
        if method == 'minmax':
            min_val = risk_map.min()
            max_val = risk_map.max()
            if max_val - min_val == 0:
                return np.zeros_like(risk_map)
            return (risk_map - min_val) / (max_val - min_val)
        
        elif method == 'zscore':
            mean = risk_map.mean()
            std = risk_map.std()
            if std == 0:
                return np.zeros_like(risk_map)
            return (risk_map - mean) / std
        
        elif method == 'log':
            return np.log1p(risk_map) / np.log1p(risk_map.max())
        
        else:
            raise ValueError(f"Unknown normalization method: {method}")
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
