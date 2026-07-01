"""
Noise Impact Risk Model for UAV Operations

Implements noise impact cost based on Eq. 17 from Pang et al. (2022):
c_noise = L(sl) = ϖ × Lh × [1 / (h² + d²)]

Where:
- c_noise: Cost of noise impact in given airspace unit
- ϖ (varpi): Conversion factor from sound intensity to sound level
- Lh: Reference noise produced by drone (55 dB) [55]
- h: Flight altitude (m)
- d: Horizontal distance from point directly under UAV (30 feet ≈ 9.144m) [54]

Sound intensity at height h and distance d:
I(si) = 1 / (h² + d²)

Sound level conversion:
L(sl) = ϖ × Lh × I(si)

Noise impact is NOT considered if flying height exceeds the threshold
corresponding to 40 dB noise level [56,57].
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Optional

try:
    from .base_risk import BaseRiskModel
    from .risk_config import NOISE_RISK
except ImportError:
    from base_risk import BaseRiskModel
    from risk_config import NOISE_RISK


class NoiseRiskModel(BaseRiskModel):
    """
    Noise impact risk model for UAV operations.
    
    Computes noise cost based on sound propagation physics.
    Implements Eq. 17 from Pang et al. (2022).
    """
    
    def __init__(self, parameters: Optional[Dict[str, Any]] = None):
        """
        Initialize noise risk model.
        
        Parameters:
            parameters: Optional dict to override default parameters
        """
        # Get configuration with defaults first
        self.conversion_factor = NOISE_RISK['conversion_factor']  # ϖ (varpi)
        self.reference_noise_db = NOISE_RISK['reference_noise_db']  # Lh = 55 dB
        self.horizontal_distance_m = NOISE_RISK['horizontal_distance_m']  # d = 30 feet ≈ 9.144m
        self.noise_threshold_db = NOISE_RISK['noise_threshold_db']  # 40 dB threshold
        
        # Override with provided parameters
        if parameters:
            self.conversion_factor = parameters.get('conversion_factor', self.conversion_factor)
            self.reference_noise_db = parameters.get('reference_noise_db', self.reference_noise_db)
            self.horizontal_distance_m = parameters.get('horizontal_distance_m', self.horizontal_distance_m)
            self.noise_threshold_db = parameters.get('noise_threshold_db', self.noise_threshold_db)
        
        super().__init__("noise_impact", parameters or {})
        
        print(f"[NoiseRiskModel] Initialized with:")
        print(f"  - Conversion factor (ϖ): {self.conversion_factor}")
        print(f"  - Reference noise (Lh): {self.reference_noise_db} dB")
        print(f"  - Horizontal distance (d): {self.horizontal_distance_m:.3f} m (30 feet)")
        print(f"  - Threshold: {self.noise_threshold_db} dB")
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Return default parameters for noise risk model."""
        return {
            'conversion_factor': NOISE_RISK['conversion_factor'],
            'reference_noise_db': NOISE_RISK['reference_noise_db'],
            'horizontal_distance_m': NOISE_RISK['horizontal_distance_m'],
            'noise_threshold_db': NOISE_RISK['noise_threshold_db'],
        }
    
    def validate_parameters(self) -> bool:
        """Validate noise risk parameters."""
        if self.conversion_factor <= 0:
            raise ValueError("Conversion factor must be positive")
        if self.reference_noise_db <= 0:
            raise ValueError("Reference noise level must be positive")
        if self.horizontal_distance_m <= 0:
            raise ValueError("Horizontal distance must be positive")
        if self.noise_threshold_db <= 0:
            raise ValueError("Noise threshold must be positive")
        return True
    
    def compute_height_threshold(self) -> float:
        """
        Compute the altitude threshold where noise drops to acceptable level.
        
        Based on references [56,57], threshold corresponds to 40 dB noise level.
        
        Using the formula:
        c_noise = ϖ × Lh × [1 / (h² + d²)] = threshold_db
        
        Solving for h:
        h_threshold = √[(ϖ × Lh / threshold_db) - d²]
        
        Returns:
            Height threshold (m) above which noise is not considered
        """
        # c_noise = ϖ × Lh / (h² + d²) = threshold_db
        # h² + d² = ϖ × Lh / threshold_db
        # h² = (ϖ × Lh / threshold_db) - d²
        
        numerator = self.conversion_factor * self.reference_noise_db
        denominator = self.noise_threshold_db
        
        h_squared = (numerator / denominator) - (self.horizontal_distance_m ** 2)
        
        if h_squared <= 0:
            # If calculation gives negative, return a reasonable default
            return 100.0
        
        h_threshold = np.sqrt(h_squared)
        return h_threshold
    
    def compute_sound_intensity(self, altitude: float, horizontal_distance: Optional[float] = None) -> float:
        """
        Compute sound intensity I(si) = 1 / (h² + d²)
        
        Parameters:
            altitude: Flight altitude (m)
            horizontal_distance: Horizontal distance (m), uses default if None
            
        Returns:
            Sound intensity value
        """
        if horizontal_distance is None:
            horizontal_distance = self.horizontal_distance_m
        
        # I(si) = 1 / (h² + d²)
        intensity = 1.0 / (altitude**2 + horizontal_distance**2)
        
        return intensity
    
    def compute_sound_level(self, altitude: float, horizontal_distance: Optional[float] = None) -> float:
        """
        Compute sound level L(sl) = ϖ × Lh × I(si)
        
        Parameters:
            altitude: Flight altitude (m)
            horizontal_distance: Horizontal distance (m), uses default if None
            
        Returns:
            Sound level (dB)
        """
        # Get sound intensity
        intensity = self.compute_sound_intensity(altitude, horizontal_distance)
        
        # L(sl) = ϖ × Lh × I(si)
        sound_level = self.conversion_factor * self.reference_noise_db * intensity
        
        return sound_level
    
    def compute_noise_cost_formula_17(
        self,
        altitude: float,
        horizontal_distance: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Compute noise cost using Eq. 17: c_noise = ϖ × Lh × [1 / (h² + d²)]
        
        Parameters:
            altitude: Flight altitude (m)
            horizontal_distance: Horizontal distance array (m), uses default if None
            
        Returns:
            Noise cost array
        """
        if horizontal_distance is None:
            # Use default distance (30 feet)
            d_array = np.array([self.horizontal_distance_m])
        else:
            d_array = np.asarray(horizontal_distance, dtype=float)
        
        # Ensure altitude is array-compatible
        h = float(altitude)
        
        # Compute denominator: h² + d²
        denominator = h**2 + d_array**2
        
        # Avoid division by zero
        denominator = np.maximum(denominator, 1e-10)
        
        # Apply Eq. 17: c_noise = ϖ × Lh × [1 / (h² + d²)]
        noise_cost = self.conversion_factor * self.reference_noise_db / denominator
        
        return noise_cost
    
    def apply_height_threshold(
        self, 
        noise_cost: np.ndarray, 
        altitude: float
    ) -> np.ndarray:
        """
        Apply height threshold: set noise cost to 0 if altitude exceeds threshold.
        
        Parameters:
            noise_cost: Computed noise cost array
            altitude: Current flight altitude (m)
            
        Returns:
            Thresholded noise cost array
        """
        h_threshold = self.compute_height_threshold()
        
        # If flying above threshold, noise impact is negligible
        if altitude > h_threshold:
            return np.zeros_like(noise_cost)
        
        return noise_cost
    
    def compute_risk(
        self,
        grid,
        data: Dict[str, Any],
        altitude_override: Optional[float] = None,
        **kwargs
    ) -> np.ndarray:
        """
        Compute noise impact risk for entire grid at given altitude.
        
        Parameters:
            grid: Grid3D object with spatial information
            data: Dictionary containing required data arrays
                - 'population_density': Population density array (people/km²)
            altitude_override: Override grid layer altitude (optional)
            
        Returns:
            Noise risk array with shape (grid.height, grid.width)
        """
        # Get population density (required for weighted noise impact)
        if 'population_density' not in data:
            raise ValueError("Population density data required for noise risk calculation")
        
        population_density = data['population_density']
        
        # Determine altitude
        if altitude_override is not None:
            altitude = altitude_override
        else:
            # Use first layer altitude as default
            altitude = 50.0
        
        # For each grid cell, compute noise cost
        # In this simplified version, we assume uniform distance d = 30 feet
        total_cells = population_density.size
        noise_cost_flat = self.compute_noise_cost_formula_17(altitude)
        
        # Apply height threshold
        noise_cost_flat = self.apply_height_threshold(noise_cost_flat, altitude)
        
        # Broadcast to match grid size
        noise_cost_array = np.full(total_cells, noise_cost_flat[0])
        
        # Reshape to 2D grid
        noise_cost_2d = noise_cost_array.reshape(population_density.shape)
        
        # Weight by population density (more people = higher impact)
        # Normalize population density to avoid extreme values
        pop_max = population_density.max()
        if pop_max > 0:
            pop_normalized = population_density / pop_max
        else:
            pop_normalized = np.ones_like(population_density)
        
        # Final noise risk = noise cost × population exposure
        noise_risk = noise_cost_2d * pop_normalized
        
        return noise_risk