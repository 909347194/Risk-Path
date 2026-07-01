"""
Population Density Model

Implements population density estimation using gravity-based model (Eq. 11).
This can be used to generate population density maps from amenity locations.

Eq. 11: σ_p = exp(1 - r²) × σ_p_avg
where:
  - σ_p_avg: Average population density
  - r: Distance to nearest amenity (km)
  - Gravity radius: 1 km
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from scipy.spatial import KDTree

try:
    from .base_risk import BaseRiskModel
    from .risk_config import FATALITY_RISK
except ImportError:
    from base_risk import BaseRiskModel
    from risk_config import FATALITY_RISK


class PopulationDensityModel:
    """Population density estimation using gravity model (Eq. 11).
    
    Models population distribution around amenities:
    - High density within 0.3 km of amenities
    - Linear decrease from 0.3 km to 1.0 km
    - Minimal density beyond 1.0 km
    
    This matches the pattern described in the paper (Fig. 3).
    """
    
    def __init__(
        self,
        sigma_p_avg: float = 10000.0,
        gravity_radius: float = 1.0,
        high_density_threshold: float = 0.3,
    ):
        """
        Args:
            sigma_p_avg: Average population density (people per km²)
            gravity_radius: Maximum influence radius (km), default 1.0
            high_density_threshold: Distance for high density (km), default 0.3
        """
        self.sigma_p_avg = sigma_p_avg
        self.gravity_radius = gravity_radius
        self.high_density_threshold = high_density_threshold
    
    def compute_population_density(
        self,
        amenities: np.ndarray,
        x_coords: np.ndarray,
        y_coords: np.ndarray,
    ) -> np.ndarray:
        """Compute population density map based on amenity locations (Eq. 11).
        
        Args:
            amenities: Array of amenity locations [(x1, y1), (x2, y2), ...] in meters
            x_coords: X coordinates of grid cells (meters)
            y_coords: Y coordinates of grid cells (meters)
            
        Returns:
            2D population density array (people per km²)
        """
        # Build KDTree for fast nearest amenity query
        amenity_tree = KDTree(amenities)
        
        # Create grid
        X, Y = np.meshgrid(x_coords, y_coords, indexing='ij')
        grid_points = np.column_stack([X.ravel(), Y.ravel()])
        
        # Find distance to nearest amenity (in km)
        distances, _ = amenity_tree.query(grid_points)
        distances_km = distances / 1000.0  # Convert to km
        
        # Eq. 11: σ_p = exp(1 - r²) × σ_p_avg
        # Clip radius to gravity_radius
        distances_km = np.clip(distances_km, 0, self.gravity_radius)
        
        population_density = np.exp(1 - distances_km**2) * self.sigma_p_avg
        
        # Reshape to 2D
        density_map = population_density.reshape(len(x_coords), len(y_coords))
        
        return density_map
    
    def compute_density_at_point(
        self,
        point: Tuple[float, float],
        amenities: np.ndarray,
    ) -> float:
        """Compute population density at a single point.
        
        Args:
            point: (x, y) location in meters
            amenities: Array of amenity locations in meters
            
        Returns:
            Population density at point (people per km²)
        """
        amenity_tree = KDTree(amenities)
        
        # Distance to nearest amenity
        dist, _ = amenity_tree.query([point])
        r = dist / 1000.0  # Convert to km
        
        # Clip radius
        r = min(r, self.gravity_radius)
        
        # Eq. 11
        sigma_p = np.exp(1 - r**2) * self.sigma_p_avg
        
        return sigma_p
    
    def analyze_density_pattern(self) -> Dict[str, Any]:
        """Analyze the density pattern characteristics.
        
        Returns:
            Dictionary with density statistics at different distances
        """
        distances = np.linspace(0, self.gravity_radius, 100)
        densities = np.exp(1 - distances**2) * self.sigma_p_avg
        
        return {
            'max_density': float(densities[0]),
            'min_density': float(densities[-1]),
            'density_at_0km': float(densities[0]),
            'density_at_0.3km': float(np.exp(1 - 0.3**2) * self.sigma_p_avg),
            'density_at_0.5km': float(np.exp(1 - 0.5**2) * self.sigma_p_avg),
            'density_at_1.0km': float(np.exp(1 - 1.0**2) * self.sigma_p_avg),
            'avg_density': float(densities.mean()),
        }


def test_population_density_model():
    """Test the population density model."""
    import matplotlib.pyplot as plt
    
    print("=" * 70)
    print("Testing Population Density Model (Eq. 11)")
    print("=" * 70)
    
    # Initialize model
    model = PopulationDensityModel(
        sigma_p_avg=10000,  # 10,000 people per km²
        gravity_radius=1.0,  # 1 km
    )
    
    # Analyze pattern
    pattern = model.analyze_density_pattern()
    
    print("\n✓ Population Density Pattern:")
    print(f"  At 0.0 km: {pattern['density_at_0km']:.0f} people/km²")
    print(f"  At 0.3 km: {pattern['density_at_0.3km']:.0f} people/km²")
    print(f"  At 0.5 km: {pattern['density_at_0.5km']:.0f} people/km²")
    print(f"  At 1.0 km: {pattern['density_at_1.0km']:.0f} people/km²")
    print(f"  Average: {pattern['avg_density']:.0f} people/km²")
    
    # Create synthetic amenities (e.g., city centers, transit stations)
    amenities = np.array([
        [500, 500],    # Amenity 1
        [1500, 1500],  # Amenity 2
        [2500, 500],   # Amenity 3
        [500, 2500],   # Amenity 4
        [2000, 2000],  # Amenity 5
    ])
    
    print(f"\n✓ Created {len(amenities)} synthetic amenities")
    
    # Create grid
    x_coords = np.arange(0, 3000, 30)  # 0-3km, 30m resolution
    y_coords = np.arange(0, 3000, 30)
    
    print(f"  Grid: {len(x_coords)} × {len(y_coords)} = {len(x_coords)*len(y_coords)} cells")
    print(f"  Resolution: 30m")
    
    # Compute population density
    density_map = model.compute_population_density(amenities, x_coords, y_coords)
    
    print(f"\n✓ Population density map:")
    print(f"  Shape: {density_map.shape}")
    print(f"  Min: {density_map.min():.0f} people/km²")
    print(f"  Max: {density_map.max():.0f} people/km²")
    print(f"  Mean: {density_map.mean():.0f} people/km²")
    
    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Population density map
    im1 = axes[0].imshow(
        density_map.T,
        cmap='YlOrRd',
        origin='lower',
        extent=[0, 3, 0, 3]
    )
    axes[0].scatter(
        amenities[:, 0] / 1000, amenities[:, 1] / 1000,
        c='blue', s=100, marker='*', label='Amenities'
    )
    axes[0].set_title('Population Density (Eq. 11)\nσ_p = exp(1 - r²) × σ_p_avg', fontsize=11)
    axes[0].set_xlabel('Distance (km)')
    axes[0].set_ylabel('Distance (km)')
    axes[0].legend()
    plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04, label='People per km²')
    
    # Plot 2: Density vs distance curve
    distances = np.linspace(0, 1.5, 100)
    densities = np.exp(1 - np.clip(distances, 0, 1.0)**2) * model.sigma_p_avg
    
    axes[1].plot(distances, densities, 'b-', linewidth=2)
    axes[1].axvline(x=0.3, color='r', linestyle='--', alpha=0.7, label='High density threshold')
    axes[1].axvline(x=1.0, color='g', linestyle='--', alpha=0.7, label='Gravity radius')
    axes[1].fill_between(distances, 0, densities, alpha=0.3)
    axes[1].set_xlabel('Distance to Amenity (km)', fontsize=11)
    axes[1].set_ylabel('Population Density (people/km²)', fontsize=11)
    axes[1].set_title('Population Density Decay Pattern (Fig. 3)', fontsize=11)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save
    output_dir = Path(__file__).parent.parent.parent / "visualizations" / "risk_models"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "population_density_model.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")
    
    print("\n" + "=" * 70)
    print("✓ Population Density Model Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_population_density_model()
