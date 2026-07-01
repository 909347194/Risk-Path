"""
Property Damage Risk Model

Implements property damage risk based on building height distribution (Eq. 13-14).
Uses log-normal distribution to model building collision probability.

Eq. 13: ψ(h; μ, σ) = (1 / (h × σ × √(2π))) × exp(-(ln(h) - μ)² / (2σ²))
Eq. 14: c_r_p_d = ψ(e^μ) for h ≤ e^μ
         c_r_p_d = ψ(h) for h > e^μ

Based on: Pang et al. (2022) - Section on Property Damage Risk
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

try:
    from .base_risk import BaseRiskModel
    from .risk_config import PROPERTY_RISK
except ImportError:
    from base_risk import BaseRiskModel
    from risk_config import PROPERTY_RISK


class PropertyDamageRiskModel(BaseRiskModel):
    """Property damage risk model based on building height distribution.
    
    Models collision probability with buildings using log-normal distribution:
    - Building heights follow log-normal distribution (not normal)
    - Lower buildings (< e^μ) are dense → high risk
    - Higher buildings (> e^μ) have decreasing risk
    
    Key Equations:
    - Eq. 13: Log-normal probability density function
    - Eq. 14: Property damage risk cost with height threshold
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        Args:
            parameters: Property damage risk parameters (uses defaults if None)
        """
        super().__init__(name='property', parameters=parameters)
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Default property damage risk parameters."""
        return {
            'building_value_per_m2': 10000.0,  # CNY/m² (example)
            'damage_coefficient': 1.0,  # damage scaling factor
            **PROPERTY_RISK,
        }
    
    def validate_parameters(self) -> bool:
        """Validate property damage risk parameters."""
        required_params = ['mu', 'sigma', 'building_value_per_m2']
        
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")
            
            value = self.parameters[param]
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter {param} must be numeric")
        
        # mu and sigma must be positive
        if self.parameters['mu'] <= 0:
            raise ValueError(f"Parameter 'mu' must be positive, got {self.parameters['mu']}")
        
        if self.parameters['sigma'] <= 0:
            raise ValueError(f"Parameter 'sigma' must be positive, got {self.parameters['sigma']}")
        
        return True
    
    def log_normal_pdf(
        self,
        height: np.ndarray,
        mu: Optional[float] = None,
        sigma: Optional[float] = None,
    ) -> np.ndarray:
        """Compute log-normal probability density (Eq. 13).
        
        ψ(h; μ, σ) = (1 / (h × σ × √(2π))) × exp(-(ln(h) - μ)² / (2σ²))
        
        Args:
            height: Building height(s) in meters
            mu: Mean of log variable (μ)
            sigma: Standard deviation of log variable (σ)
            
        Returns:
            Log-normal probability density value(s)
        """
        mu = mu if mu is not None else self.parameters['mu']
        sigma = sigma if sigma is not None else self.parameters['sigma']
        
        # Avoid log(0) by clipping
        height = np.clip(height, 1e-6, None)
        
        # Eq. 13: Log-normal PDF
        log_h = np.log(height)
        psi = (1.0 / (height * sigma * np.sqrt(2 * np.pi))) * \
              np.exp(-((log_h - mu)**2) / (2 * sigma**2))
        
        return psi
    
    def compute_property_damage_risk(
        self,
        building_heights: np.ndarray,
        mu: Optional[float] = None,
        sigma: Optional[float] = None,
    ) -> np.ndarray:
        """Compute property damage risk cost (Eq. 14).
        
        c_r_p_d = ψ(e^μ) for h ≤ e^μ  (dense buildings, high risk)
        c_r_p_d = ψ(h) for h > e^μ    (decreasing risk with height)
        
        Args:
            building_heights: 2D array of building heights (meters)
            mu: Log-normal mean parameter (μ)
            sigma: Log-normal std parameter (σ)
            
        Returns:
            Property damage risk cost map (same shape as building_heights)
        """
        mu = mu if mu is not None else self.parameters['mu']
        sigma = sigma if sigma is not None else self.parameters['sigma']
        
        # Height threshold: e^μ
        height_threshold = np.exp(mu)
        
        # Create output array
        c_r_p_d = np.zeros_like(building_heights, dtype=float)
        
        # Case 1: h ≤ e^μ → use risk at threshold (dense buildings)
        mask_low = building_heights <= height_threshold
        if np.any(mask_low):
            psi_threshold = self.log_normal_pdf(height_threshold, mu, sigma)
            c_r_p_d[mask_low] = psi_threshold
        
        # Case 2: h > e^μ → use actual height
        mask_high = building_heights > height_threshold
        if np.any(mask_high):
            c_r_p_d[mask_high] = self.log_normal_pdf(
                building_heights[mask_high], mu, sigma
            )
        
        return c_r_p_d
    
    def compute_integrated_property_cost(
        self,
        building_heights: np.ndarray,
        building_footprints: Optional[np.ndarray] = None,
        building_values: Optional[np.ndarray] = None,
        mu: Optional[float] = None,
        sigma: Optional[float] = None,
    ) -> np.ndarray:
        """Compute integrated property damage cost.
        
        Combines:
        - Collision probability (from building height)
        - Building footprint area (optional)
        - Building value (optional)
        
        Args:
            building_heights: Building height map (meters)
            building_footprints: Building footprint area per cell (m²)
            building_values: Building value per cell (CNY)
            mu: Log-normal mean parameter
            sigma: Log-normal std parameter
            
        Returns:
            Integrated property damage cost map
        """
        # Get collision probability (risk cost)
        c_r_p_d = self.compute_property_damage_risk(building_heights, mu, sigma)
        
        # Apply building value if provided
        if building_values is not None:
            # Scale by building value
            c_r_p_d = c_r_p_d * building_values
        
        # Apply footprint area if provided
        if building_footprints is not None:
            # Scale by footprint
            c_r_p_d = c_r_p_d * building_footprints
        
        # Apply damage coefficient
        damage_coeff = self.parameters.get('damage_coefficient', 1.0)
        c_r_p_d = c_r_p_d * damage_coeff
        
        return c_r_p_d
    
    def create_synthetic_building_heights(
        self,
        shape: Tuple[int, int],
        mu: Optional[float] = None,
        sigma: Optional[float] = None,
        seed: int = 42,
    ) -> np.ndarray:
        """Create synthetic building height map from log-normal distribution.
        
        Args:
            shape: Grid shape (height, width)
            mu: Log-normal mean parameter
            sigma: Log-normal std parameter
            seed: Random seed
            
        Returns:
            Synthetic building height array (meters)
        """
        mu = mu if mu is not None else self.parameters['mu']
        sigma = sigma if sigma is not None else self.parameters['sigma']
        
        np.random.seed(seed)
        
        # Sample from log-normal distribution
        heights = np.random.lognormal(mean=mu, sigma=sigma, size=shape)
        
        # Clip to realistic range (0-300m)
        heights = np.clip(heights, 0, 300)
        
        return heights
    
    def estimate_parameters_from_data(
        self,
        building_heights: np.ndarray,
    ) -> Tuple[float, float]:
        """Estimate mu and sigma from actual building height data.
        
        Args:
            building_heights: Array of building heights (non-zero values)
            
        Returns:
            Tuple of (mu, sigma) parameters
        """
        # Filter out zero heights (no buildings)
        heights = building_heights[building_heights > 0]
        
        if len(heights) == 0:
            raise ValueError("No building data found (all heights are zero)")
        
        # Log-normal parameter estimation
        log_heights = np.log(heights)
        
        mu = log_heights.mean()
        sigma = log_heights.std()
        
        return mu, sigma
    
    def compute_risk(
        self,
        grid,
        data: Dict[str, Any],
        **kwargs
    ) -> np.ndarray:
        """Compute property damage risk.
        
        Args:
            grid: Grid3D object (not used, building heights from data)
            data: Dictionary containing:
                  - 'building_heights': 2D array of building heights (meters)
                  - 'building_footprints': Optional, footprint area (m²)
                  - 'building_values': Optional, building value (CNY)
            **kwargs: Additional parameters
        
        Returns:
            Property damage risk cost map (2D array)
        """
        if 'building_heights' not in data:
            raise ValueError("data must contain 'building_heights'")
        
        building_heights = data['building_heights']
        building_footprints = data.get('building_footprints', None)
        building_values = data.get('building_values', None)
        
        # Compute integrated property cost
        risk_map = self.compute_integrated_property_cost(
            building_heights,
            building_footprints=building_footprints,
            building_values=building_values,
        )
        
        return risk_map


def test_property_damage_risk():
    """Test property damage risk model."""
    import matplotlib.pyplot as plt
    
    print("=" * 70)
    print("Testing Property Damage Risk Model (Eq. 13-14)")
    print("=" * 70)
    
    # Initialize model
    model = PropertyDamageRiskModel(parameters={
        'mu': 2.5,  # log-mean (corresponds to ~12m median height)
        'sigma': 0.8,  # log-std
        'building_value_per_m2': 10000.0,  # CNY/m²
    })
    
    print(f"\n✓ Initialized: {model}")
    print(f"  Parameters: μ={model.parameters['mu']}, σ={model.parameters['sigma']}")
    print(f"  Height threshold: e^{model.parameters['mu']} = {np.exp(model.parameters['mu']):.1f}m")
    print(f"  Building value: {model.parameters['building_value_per_m2']} CNY/m²")
    
    # Test log-normal PDF
    print("\n" + "=" * 70)
    print("Log-Normal Distribution Analysis")
    print("=" * 70)
    
    heights_test = np.array([5, 10, 15, 20, 30, 50, 100])
    
    for h in heights_test:
        psi = model.log_normal_pdf(h)
        threshold = np.exp(model.parameters['mu'])
        risk = model.compute_property_damage_risk(np.array([h]))[0]
        
        print(f"\n  Height: {h:3.0f}m", end="")
        if h <= threshold:
            print(f" (≤ {threshold:.1f}m threshold)", end="")
        else:
            print(f" (> {threshold:.1f}m threshold)", end="")
        print()
        print(f"    PDF ψ(h): {psi:.6f}")
        print(f"    Risk cost: {risk:.6f}")
    
    # Create synthetic building heights
    print("\n" + "=" * 70)
    print("Synthetic Building Height Map")
    print("=" * 70)
    
    building_heights = model.create_synthetic_building_heights(
        shape=(100, 100),
        seed=42
    )
    
    print(f"\n✓ Synthetic building heights:")
    print(f"  Shape: {building_heights.shape}")
    print(f"  Range: {building_heights.min():.1f} - {building_heights.max():.1f} m")
    print(f"  Mean: {building_heights.mean():.1f} m")
    print(f"  Median: {np.median(building_heights):.1f} m")
    
    # Compute property damage risk
    risk_map = model.compute_property_damage_risk(building_heights)
    
    stats = model.get_risk_statistics(risk_map)
    
    print(f"\n✓ Property damage risk:")
    print(f"  Min: {stats['min']:.6e}")
    print(f"  Max: {stats['max']:.6e}")
    print(f"  Mean: {stats['mean']:.6e}")
    print(f"  Total: {stats['total']:.6e}")
    
    # Visualization
    print("\n" + "=" * 70)
    print("Generating Visualizations...")
    print("=" * 70)
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    
    # Plot 1: Building heights
    im1 = axes[0, 0].imshow(building_heights, cmap='viridis', origin='lower')
    axes[0, 0].set_title('Building Heights (m)\n(Log-normal distribution)', fontsize=11)
    axes[0, 0].set_xlabel('X (cells)')
    axes[0, 0].set_ylabel('Y (cells)')
    plt.colorbar(im1, ax=axes[0, 0], fraction=0.046, pad=0.04, label='Height (m)')
    
    # Plot 2: Property damage risk
    im2 = axes[0, 1].imshow(risk_map, cmap='hot', origin='lower')
    axes[0, 1].set_title('Property Damage Risk\n(Eq. 13-14)', fontsize=11)
    axes[0, 1].set_xlabel('X (cells)')
    axes[0, 1].set_ylabel('Y (cells)')
    plt.colorbar(im2, ax=axes[0, 1], fraction=0.046, pad=0.04, label='Risk cost')
    
    # Plot 3: Log-normal PDF curve
    heights_range = np.linspace(1, 150, 100)
    pdf_values = model.log_normal_pdf(heights_range)
    
    axes[1, 0].plot(heights_range, pdf_values, 'b-', linewidth=2)
    threshold = np.exp(model.parameters['mu'])
    axes[1, 0].axvline(x=threshold, color='r', linestyle='--', 
                       label=f'Threshold e^μ = {threshold:.1f}m')
    axes[1, 0].fill_between(heights_range, 0, pdf_values, alpha=0.3)
    axes[1, 0].set_xlabel('Building Height (m)', fontsize=11)
    axes[1, 0].set_ylabel('Probability Density ψ(h)', fontsize=11)
    axes[1, 0].set_title('Log-Normal Distribution (Eq. 13)', fontsize=11)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3)
    
    # Plot 4: Risk cost vs height
    risk_values = model.compute_property_damage_risk(heights_range)
    
    axes[1, 1].plot(heights_range, risk_values, 'g-', linewidth=2)
    axes[1, 1].axvline(x=threshold, color='r', linestyle='--',
                       label=f'Threshold e^μ = {threshold:.1f}m')
    axes[1, 1].set_xlabel('Building Height (m)', fontsize=11)
    axes[1, 1].set_ylabel('Property Damage Risk c_r_p_d', fontsize=11)
    axes[1, 1].set_title('Property Damage Risk (Eq. 14)', fontsize=11)
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save
    output_dir = Path(__file__).parent.parent / "visualizations" / "risk_models"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "property_damage_risk.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")
    
    print("\n" + "=" * 70)
    print("✓ Property Damage Risk Model Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_property_damage_risk()
