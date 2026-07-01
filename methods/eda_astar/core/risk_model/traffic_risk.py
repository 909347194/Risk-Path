"""
Traffic Density Risk Model

Implements vehicle exposure risk based on road network density.
Uses Eq. 10 from the paper and pre-computed traffic density from road_density.py.

Eq. 10: N_hit^v = S_hit × σ_v
where:
  - S_hit: UAV crash impact area (m²)
  - σ_v: Vehicle density in road network (vehicles per unit area)
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from .base_risk import BaseRiskModel
    from .risk_config import UAV_IMPACT_AREA, TRAFFIC_RISK
except ImportError:
    from base_risk import BaseRiskModel
    from risk_config import UAV_IMPACT_AREA, TRAFFIC_RISK


class TrafficRiskModel(BaseRiskModel):
    """Traffic density risk model for UAV crashes.
    
    Computes vehicle exposure risk based on:
    - Road network density (σ_v)
    - UAV impact area (S_hit)
    - Expected vehicles hit (N_hit^v)
    
    Key Equation:
    - Eq. 10: N_hit^v = S_hit × σ_v
    
    This model uses pre-computed traffic density from road_density.py
    which implements the Gaussian attraction model (Eq. 12).
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        Args:
            parameters: Traffic risk parameters (uses defaults if None)
        """
        super().__init__(name='traffic', parameters=parameters)
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Default traffic risk parameters."""
        return {
            'uav_impact_area': UAV_IMPACT_AREA,
            **TRAFFIC_RISK,
        }
    
    def validate_parameters(self) -> bool:
        """Validate traffic risk parameters."""
        required_params = ['uav_impact_area', 'sigma_v_avg', 'radius']
        
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")
            
            value = self.parameters[param]
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter {param} must be numeric")
            
            if value < 0:
                raise ValueError(f"Parameter {param} must be non-negative")
        
        return True
    
    def load_traffic_density(
        self,
        traffic_density_file: Optional[str] = None,
        metadata_file: Optional[str] = None,
    ) -> tuple[np.ndarray, Dict[str, Any]]:
        """Load pre-computed traffic density from road_density.py output.
        
        Args:
            traffic_density_file: Path to traffic_density.npy
            metadata_file: Path to traffic_density_metadata.npz
            
        Returns:
            Tuple of (traffic_density_array, metadata_dict)
        """
        if traffic_density_file is None:
            # Default location
            traffic_density_file = Path(__file__).parent.parent.parent.parent / "data" / "traffic_density.npy"
        
        if metadata_file is None:
            metadata_file = Path(__file__).parent.parent.parent.parent / "data" / "traffic_density_metadata.npz"
        
        # Load traffic density
        if not Path(traffic_density_file).exists():
            raise FileNotFoundError(
                f"Traffic density file not found: {traffic_density_file}\n"
                "Please run src/utils/road_density.py first to generate it."
            )
        
        traffic_density = np.load(traffic_density_file)
        
        # Load metadata
        metadata = {}
        if Path(metadata_file).exists():
            metadata_npz = np.load(metadata_file, allow_pickle=True)
            metadata = {key: metadata_npz[key] for key in metadata_npz.files}
        
        return traffic_density, metadata
    
    def compute_vehicles_hit(
        self,
        vehicle_density: np.ndarray,
        impact_area: Optional[float] = None,
    ) -> np.ndarray:
        """Compute expected number of vehicles hit (Eq. 10).
        
        N_hit^v = S_hit × σ_v
        
        Args:
            vehicle_density: Vehicle density map (vehicles per unit area)
            impact_area: UAV crash impact area S_hit (m²)
            
        Returns:
            Expected vehicles hit per cell
        """
        S_hit = impact_area or self.parameters['uav_impact_area']
        
        # Eq. 10
        N_hit_v = S_hit * vehicle_density
        
        return N_hit_v
    
    def compute_traffic_risk_cost(
        self,
        vehicle_density: np.ndarray,
        crash_probability: Optional[float] = None,
        impact_area: Optional[float] = None,
    ) -> np.ndarray:
        """Compute traffic risk cost.
        
        c_r_traffic = P_crash × N_hit^v
                    = P_crash × S_hit × σ_v
        
        Args:
            vehicle_density: Vehicle density map
            crash_probability: UAV crash probability P_crash
            impact_area: UAV impact area S_hit
            
        Returns:
            Traffic risk cost map
        """
        P_crash = crash_probability or self.parameters.get('crash_probability', 1e-4)
        S_hit = impact_area or self.parameters['uav_impact_area']
        
        # Expected vehicles hit
        N_hit_v = self.compute_vehicles_hit(vehicle_density, S_hit)
        
        # Risk cost
        c_r_traffic = P_crash * N_hit_v
        
        return c_r_traffic
    
    def compute_risk(
        self,
        grid,
        data: Dict[str, Any],
        traffic_density_source: Optional[str] = None,
        **kwargs
    ) -> np.ndarray:
        """Compute traffic density risk.
        
        Args:
            grid: Grid3D object (used for grid dimensions)
            data: Dictionary containing:
                  - 'traffic_density': Pre-computed traffic density (optional)
                  If not provided, loads from file
            traffic_density_source: Path to traffic density file (optional)
            **kwargs: Additional parameters
        
        Returns:
            Traffic risk map (2D array)
        """
        # Get traffic density
        if 'traffic_density' in data:
            # Use provided density
            traffic_density = data['traffic_density']
        elif traffic_density_source is not None:
            # Load from specified file
            traffic_density, _ = self.load_traffic_density(traffic_density_source)
        else:
            # Load from default location
            traffic_density, metadata = self.load_traffic_density()
            
            # Verify grid dimensions match
            if grid is not None:
                if (traffic_density.shape[0] != grid.height or 
                    traffic_density.shape[1] != grid.width):
                    raise ValueError(
                        f"Traffic density shape {traffic_density.shape} doesn't match "
                        f"grid dimensions ({grid.height}, {grid.width})"
                    )
        
        # Compute traffic risk cost
        risk_map = self.compute_traffic_risk_cost(traffic_density)
        
        return risk_map
    
    def create_synthetic_vehicle_density(
        self,
        shape: tuple[int, int],
        seed: int = 42,
        pattern: str = 'grid'
    ) -> np.ndarray:
        """Create synthetic vehicle density for testing.
        
        Args:
            shape: Grid shape (height, width)
            seed: Random seed
            pattern: Pattern type ('grid', 'random', 'radial')
            
        Returns:
            Synthetic vehicle density array
        """
        np.random.seed(seed)
        
        if pattern == 'grid':
            # Simulate road grid
            density = np.zeros(shape)
            
            # Horizontal roads
            for i in range(0, shape[0], shape[0] // 5):
                density[i:i+2, :] = np.random.uniform(50, 200, (2, shape[1]))
            
            # Vertical roads
            for j in range(0, shape[1], shape[1] // 5):
                density[:, j:j+2] = np.random.uniform(50, 200, (shape[0], 2))
            
            # Add intersections (higher density)
            for i in range(0, shape[0], shape[0] // 5):
                for j in range(0, shape[1], shape[1] // 5):
                    density[i:i+2, j:j+2] = np.random.uniform(200, 500, (2, 2))
        
        elif pattern == 'random':
            # Random vehicle distribution
            density = np.random.uniform(0, 100, shape)
        
        elif pattern == 'radial':
            # Higher density in center (urban area)
            y, x = np.ogrid[:shape[0], :shape[1]]
            center_y, center_x = shape[0] // 2, shape[1] // 2
            
            density = np.exp(
                -((x - center_x)**2 + (y - center_y)**2) / (2 * (shape[0] // 4)**2)
            ) * 300
            
            # Add some road-like structures
            for i in range(0, shape[0], shape[0] // 6):
                density[i:i+2, :] += 100
            for j in range(0, shape[1], shape[1] // 6):
                density[:, j:j+2] += 100
        
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
        
        return density
