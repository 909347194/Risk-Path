"""
Test Traffic Density Risk Model

Demonstrates how to:
1. Use pre-computed traffic density from road_density.py
2. Create synthetic vehicle density for testing
3. Compute traffic risk using Eq. 10
4. Visualize traffic risk maps
"""

import sys
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.risk_model.traffic_risk import TrafficRiskModel


def test_traffic_risk_with_real_data():
    """Test traffic risk using real data from road_density.py."""
    
    print("=" * 70)
    print("Testing Traffic Risk Model with Real Data (Eq. 10)")
    print("=" * 70)
    
    # Initialize model
    model = TrafficRiskModel()
    print(f"\n✓ Initialized: {model}")
    print(f"  UAV impact area: {model.parameters['uav_impact_area']} m²")
    print(f"  Avg traffic density: {model.parameters['sigma_v_avg']}")
    
    # Try to load real traffic density
    try:
        traffic_density, metadata = model.load_traffic_density()
        print(f"\n✓ Loaded real traffic density:")
        print(f"  Shape: {traffic_density.shape}")
        print(f"  Range: {traffic_density.min():.2f} - {traffic_density.max():.2f}")
        print(f"  Mean: {traffic_density.mean():.2f}")
        
        use_real_data = True
        
    except FileNotFoundError as e:
        print(f"\n⚠ Real data not found: {e}")
        print("  Using synthetic data instead...")
        use_real_data = False
    
    if not use_real_data:
        # Create synthetic vehicle density
        print("\n✓ Creating synthetic vehicle density...")
        traffic_density = model.create_synthetic_vehicle_density(
            shape=(100, 100),
            pattern='grid',
            seed=42
        )
        print(f"  Shape: {traffic_density.shape}")
        print(f"  Range: {traffic_density.min():.2f} - {traffic_density.max():.2f}")
        print(f"  Mean: {traffic_density.mean():.2f}")
    
    # Compute expected vehicles hit (Eq. 10)
    print("\n" + "=" * 70)
    print("Computing Vehicles Hit (Eq. 10: N_hit^v = S_hit × σ_v)")
    print("=" * 70)
    
    N_hit_v = model.compute_vehicles_hit(traffic_density)
    
    print(f"\n✓ Expected vehicles hit:")
    print(f"  Min: {N_hit_v.min():.4f}")
    print(f"  Max: {N_hit_v.max():.4f}")
    print(f"  Mean: {N_hit_v.mean():.4f}")
    print(f"  Total: {N_hit_v.sum():.4f}")
    
    # Compute traffic risk cost
    print("\n" + "=" * 70)
    print("Computing Traffic Risk Cost")
    print("=" * 70)
    
    risk_map = model.compute_traffic_risk_cost(traffic_density)
    
    stats = model.get_risk_statistics(risk_map)
    
    print(f"\n✓ Traffic risk cost:")
    print(f"  Min: {stats['min']:.4e}")
    print(f"  Max: {stats['max']:.4e}")
    print(f"  Mean: {stats['mean']:.4e}")
    print(f"  Total: {stats['total']:.4e}")
    print(f"  Non-zero cells: {stats['non_zero_count']}")
    
    # Visualization
    print("\n" + "=" * 70)
    print("Generating Visualizations...")
    print("=" * 70)
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Plot 1: Vehicle density
    im1 = axes[0].imshow(traffic_density, cmap='YlOrRd', origin='lower')
    axes[0].set_title('Vehicle Density (σ_v)\n(vehicles per unit area)', fontsize=11)
    axes[0].set_xlabel('X (cells)')
    axes[0].set_ylabel('Y (cells)')
    plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
    
    # Plot 2: Expected vehicles hit
    im2 = axes[1].imshow(N_hit_v, cmap='YlOrRd', origin='lower')
    axes[1].set_title('Expected Vehicles Hit (N_hit^v)\n(Eq. 10: S_hit × σ_v)', fontsize=11)
    axes[1].set_xlabel('X (cells)')
    axes[1].set_ylabel('Y (cells)')
    plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
    
    # Plot 3: Traffic risk cost
    im3 = axes[2].imshow(risk_map, cmap='hot', origin='lower')
    axes[2].set_title('Traffic Risk Cost\n(c_r_traffic)', fontsize=11)
    axes[2].set_xlabel('X (cells)')
    axes[2].set_ylabel('Y (cells)')
    plt.colorbar(im3, ax=axes[2], fraction=0.046, pad=0.04)
    
    plt.tight_layout()
    
    # Save figure
    output_dir = Path(__file__).parent.parent / "output" / "tests" / "test_traffic_risk"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "traffic_risk.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved visualization: {output_file}")
    
    print("\n" + "=" * 70)
    print("✓ Traffic Risk Model Test Complete!")
    print("=" * 70)


def test_traffic_risk_with_synthetic():
    """Test traffic risk with different synthetic patterns."""
    
    print("\n" + "=" * 70)
    print("Testing Traffic Risk Model - Synthetic Patterns")
    print("=" * 70)
    
    model = TrafficRiskModel()
    
    patterns = ['grid', 'radial', 'random']
    
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    
    for idx, pattern in enumerate(patterns):
        print(f"\n  Testing pattern: {pattern}")
        
        # Create synthetic density
        density = model.create_synthetic_vehicle_density(
            shape=(80, 80),
            pattern=pattern,
            seed=42
        )
        
        # Compute risk
        risk = model.compute_traffic_risk_cost(density)
        
        # Plot density
        ax = axes[0, idx]
        im1 = ax.imshow(density, cmap='YlOrRd', origin='lower')
        ax.set_title(f'Vehicle Density ({pattern})', fontsize=10)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        plt.colorbar(im1, ax=ax, fraction=0.046, pad=0.04)
        
        # Plot risk
        ax = axes[1, idx]
        im2 = ax.imshow(risk, cmap='hot', origin='lower')
        ax.set_title(f'Traffic Risk ({pattern})\nMean: {risk.mean():.4e}', fontsize=10)
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        plt.colorbar(im2, ax=ax, fraction=0.046, pad=0.04)
        
        print(f"    Density range: {density.min():.2f} - {density.max():.2f}")
        print(f"    Risk mean: {risk.mean():.4e}")
    
    plt.tight_layout()
    
    # Save figure
    output_dir = Path(__file__).parent.parent / "visualizations" / "risk_models"
    output_file = output_dir / "traffic_risk_patterns.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n✓ Saved pattern comparison: {output_file}")


if __name__ == "__main__":
    # Test with real data first
    test_traffic_risk_with_real_data()
    
    # Then test synthetic patterns
    test_traffic_risk_with_synthetic()
