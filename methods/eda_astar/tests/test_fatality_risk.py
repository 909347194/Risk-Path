"""
Test Individual Risk Models

Demonstrates how to:
1. Use FatalityRiskModel independently
2. Compute risk at different altitudes
3. Analyze risk statistics
4. Visualize risk maps

This script tests each risk model BEFORE integration.
"""

import sys
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.risk_model.fatality_risk import FatalityRiskModel


def create_synthetic_population(shape=(100, 100), seed=42):
    """Create synthetic population density for testing.
    
    Simulates urban area with:
    - High density center
    - Lower density suburbs
    - Some zero-density areas (parks, water)
    """
    np.random.seed(seed)
    
    y, x = np.ogrid[:shape[0], :shape[1]]
    
    # Center of urban area
    center_y, center_x = shape[0] // 2, shape[1] // 2
    
    # Gaussian distribution for urban density
    pop_density = np.exp(
        -((x - center_x)**2 + (y - center_y)**2) / (2 * (shape[0] // 4)**2)
    )
    
    # Add some noise
    pop_density += np.random.uniform(0, 0.2, shape)
    
    # Convert to people per km² (realistic range: 0-20000)
    pop_density = pop_density * 20000
    
    # Add some zero areas (parks)
    mask = np.random.random(shape) < 0.1
    pop_density[mask] = 0
    
    return pop_density


def test_fatality_risk():
    """Test fatality risk model at different altitudes."""
    
    print("=" * 70)
    print("Testing Fatality Risk Model (Eq. 1-9)")
    print("=" * 70)
    
    # Initialize model
    model = FatalityRiskModel()
    print(f"\n✓ Initialized: {model}")
    print(f"  Parameters: {model.parameters['uav_mass']}kg UAV, "
          f"S_hit={model.parameters['uav_impact_area']}m²")
    
    # Create synthetic population
    pop_density = create_synthetic_population((100, 100))
    print(f"\n✓ Synthetic population density:")
    print(f"  Shape: {pop_density.shape}")
    print(f"  Range: {pop_density.min():.0f} - {pop_density.max():.0f} people/km²")
    print(f"  Mean: {pop_density.mean():.0f} people/km²")
    
    # Test at different altitudes
    altitudes = [30, 60, 90, 120]  # meters
    
    print("\n" + "=" * 70)
    print("Impact Velocity and Energy by Altitude")
    print("=" * 70)
    
    for alt in altitudes:
        v = model.compute_impact_velocity(alt)
        E = model.compute_impact_energy(alt)
        S_c = model.compute_fatality_probability(E)
        
        print(f"\n  Altitude: {alt}m")
        print(f"    Impact velocity: {v:.2f} m/s")
        print(f"    Impact energy: {E:.2f} J")
        print(f"    Fatality probability: {S_c:.4f}")
    
    # Compute risk maps
    print("\n" + "=" * 70)
    print("Fatality Risk Maps")
    print("=" * 70)
    
    risk_maps = {}
    
    for alt in altitudes:
        # Create dummy grid object
        class DummyGrid:
            def __init__(self):
                self.layer_altitudes = [alt]
        
        grid = DummyGrid()
        data = {'population_density': pop_density}
        
        # Compute risk
        risk_map = model.compute_risk(grid, data, altitude_override=alt)
        risk_maps[alt] = risk_map
        
        # Statistics
        stats = model.get_risk_statistics(risk_map)
        
        print(f"\n  Altitude: {alt}m")
        print(f"    Min risk: {stats['min']:.2e}")
        print(f"    Max risk: {stats['max']:.2e}")
        print(f"    Mean risk: {stats['mean']:.2e}")
        print(f"    Total risk: {stats['total']:.2e}")
    
    # Visualization
    print("\n" + "=" * 70)
    print("Generating Risk Visualization...")
    print("=" * 70)
    
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for idx, alt in enumerate(altitudes):
        ax = axes[idx]
        
        # Plot risk map
        im = ax.imshow(
            risk_maps[alt],
            cmap='hot',
            interpolation='nearest',
            origin='lower'
        )
        
        ax.set_title(f'Altitude: {alt}m\n'
                    f'Mean risk: {risk_maps[alt].mean():.2e}',
                    fontsize=10)
        ax.set_xlabel('X (cells)')
        ax.set_ylabel('Y (cells)')
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    
    # Save figure
    output_dir = Path(__file__).parent.parent / "output" / "tests" / "test_fatality_risk"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "fatality_risk_by_altitude.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")
    
    # Also plot population density for reference
    fig, ax = plt.subplots(1, 1, figsize=(6, 5))
    im = ax.imshow(pop_density, cmap='viridis', origin='lower')
    ax.set_title('Synthetic Population Density\n(people per km²)', fontsize=12)
    ax.set_xlabel('X (cells)')
    ax.set_ylabel('Y (cells)')
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    
    pop_file = output_dir / "population_density.png"
    plt.savefig(pop_file, dpi=150, bbox_inches='tight')
    print(f"✓ Saved population map: {pop_file}")
    
    print("\n" + "=" * 70)
    print("✓ Fatality Risk Model Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_fatality_risk()
