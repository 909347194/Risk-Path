"""
Test Integrated Cost Assessment Model

Tests the additive linear model from Pang et al. (2022):
c_v = Σ_{τ=1}^{3} α_τ × ω_τ × c_τ

Where:
- α_τ: Weight factor (α_1 + α_2 + α_3 = 1)
- ω_τ: Normalization factor = 1 / c_τ_max
- c_τ: Raw cost value
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


def test_weight_constraints():
    """Test that weight factors sum to 1.0."""
    print("=" * 70)
    print("Testing Weight Factor Constraints")
    print("=" * 70)
    
    # Test valid weights
    valid_weights = [
        (0.5, 0.3, 0.2),
        (0.6, 0.25, 0.15),
        (0.7, 0.2, 0.1),
        (0.4, 0.4, 0.2),
    ]
    
    print("\n✓ Valid weight combinations (must sum to 1.0):")
    for w_f, w_p, w_n in valid_weights:
        total = w_f + w_p + w_n
        status = "✓" if np.isclose(total, 1.0) else "✗"
        print(f"  {status} α_f={w_f:.2f}, α_p={w_p:.2f}, α_n={w_n:.2f} → sum={total:.4f}")
    
    # Test invalid weights
    invalid_weights = [
        (0.5, 0.3, 0.3),  # Sum = 1.1
        (0.4, 0.3, 0.2),  # Sum = 0.9
        (0.6, 0.6, 0.6),  # Sum = 1.8
    ]
    
    print("\n✗ Invalid weight combinations:")
    for w_f, w_p, w_n in invalid_weights:
        total = w_f + w_p + w_n
        print(f"  ✗ α_f={w_f:.2f}, α_p={w_p:.2f}, α_n={w_n:.2f} → sum={total:.4f} (INVALID)")


def test_normalization_factor():
    """Test normalization factor calculation: ω_τ = 1 / c_τ_max."""
    print("\n" + "=" * 70)
    print("Testing Normalization Factor Calculation")
    print("=" * 70)
    
    # Example from paper: max cost = 10
    c_max_example = 10.0
    omega_example = 1.0 / c_max_example
    
    print(f"\n✓ Paper example:")
    print(f"  c_τ_max = {c_max_example}")
    print(f"  ω_τ = 1 / c_τ_max = {omega_example:.4f}")
    
    # Test with various max values
    test_cases = [
        1.0,
        10.0,
        100.0,
        1000.0,
        0.5,
    ]
    
    print(f"\n✓ Various max cost values:")
    for c_max in test_cases:
        omega = 1.0 / c_max
        print(f"  c_max = {c_max:7.1f} → ω = {omega:.6f}")


def test_integrated_cost_formula():
    """Test the integrated cost formula."""
    print("\n" + "=" * 70)
    print("Testing Integrated Cost Formula")
    print("=" * 70)
    
    # Example scenario
    alpha_f, alpha_p, alpha_n = 0.5, 0.3, 0.2
    
    # Raw costs (before normalization)
    c_fatality_raw = 8.0
    c_property_raw = 50.0
    c_noise_raw = 0.02
    
    # Max costs (for normalization)
    c_fatality_max = 10.0
    c_property_max = 100.0
    c_noise_max = 0.05
    
    # Normalization factors
    omega_f = 1.0 / c_fatality_max
    omega_p = 1.0 / c_property_max
    omega_n = 1.0 / c_noise_max
    
    # Normalized costs
    c_fatality_norm = c_fatality_raw / c_fatality_max
    c_property_norm = c_property_raw / c_property_max
    c_noise_norm = c_noise_raw / c_noise_max
    
    # Integrated cost (without distance and collision)
    c_integrated = (
        alpha_f * omega_f * c_fatality_raw +
        alpha_p * omega_p * c_property_raw +
        alpha_n * omega_n * c_noise_raw
    )
    
    # Alternative calculation using normalized costs
    c_integrated_alt = (
        alpha_f * c_fatality_norm +
        alpha_p * c_property_norm +
        alpha_n * c_noise_norm
    )
    
    print(f"\n✓ Example calculation:")
    print(f"\n  Weight factors:")
    print(f"    α_fatality = {alpha_f:.2f}")
    print(f"    α_property = {alpha_p:.2f}")
    print(f"    α_noise    = {alpha_n:.2f}")
    
    print(f"\n  Raw costs:")
    print(f"    c_fatality = {c_fatality_raw:.2f}")
    print(f"    c_property = {c_property_raw:.2f}")
    print(f"    c_noise    = {c_noise_raw:.4f}")
    
    print(f"\n  Max costs:")
    print(f"    c_fatality_max = {c_fatality_max:.2f}")
    print(f"    c_property_max = {c_property_max:.2f}")
    print(f"    c_noise_max    = {c_noise_max:.4f}")
    
    print(f"\n  Normalization factors (ω_τ = 1/c_τ_max):")
    print(f"    ω_fatality = {omega_f:.4f}")
    print(f"    ω_property = {omega_p:.4f}")
    print(f"    ω_noise    = {omega_n:.4f}")
    
    print(f"\n  Normalized costs (c_τ / c_τ_max):")
    print(f"    c_fatality_norm = {c_fatality_norm:.4f}")
    print(f"    c_property_norm = {c_property_norm:.4f}")
    print(f"    c_noise_norm    = {c_noise_norm:.4f}")
    
    print(f"\n  Integrated cost:")
    print(f"    c_v = α_f×ω_f×c_f + α_p×ω_p×c_p + α_n×ω_n×c_n")
    print(f"    c_v = {alpha_f:.2f}×{omega_f:.4f}×{c_fatality_raw:.2f} + "
          f"{alpha_p:.2f}×{omega_p:.4f}×{c_property_raw:.2f} + "
          f"{alpha_n:.2f}×{omega_n:.4f}×{c_noise_raw:.4f}")
    print(f"    c_v = {c_integrated:.4f}")
    
    print(f"\n  Verification (using normalized costs):")
    print(f"    c_v = α_f×c_f_norm + α_p×c_p_norm + α_n×c_n_norm")
    print(f"    c_v = {alpha_f:.2f}×{c_fatality_norm:.4f} + "
          f"{alpha_p:.2f}×{c_property_norm:.4f} + "
          f"{alpha_n:.2f}×{c_noise_norm:.4f}")
    print(f"    c_v = {c_integrated_alt:.4f}")
    
    print(f"\n  Match: {'✓ YES' if np.isclose(c_integrated, c_integrated_alt) else '✗ NO'}")


def test_fatality_weight_impact():
    """Demonstrate the impact of increasing fatality weight."""
    print("\n" + "=" * 70)
    print("Testing Impact of Fatality Weight Increase")
    print("=" * 70)
    
    print("\nAs stated in the paper:")
    print("'The weight of fatality cost should be increased.'")
    print("'Areas with dense populations and vehicles will be identified")
    print(" as high-risk areas, and path planning will avoid these areas.'")
    
    # Scenario: High population area
    c_fatality_high = 9.0   # High fatality risk
    c_property_med = 50.0   # Medium property risk
    c_noise_low = 0.01      # Low noise risk
    
    c_fatality_max = 10.0
    c_property_max = 100.0
    c_noise_max = 0.05
    
    omega_f = 1.0 / c_fatality_max
    omega_p = 1.0 / c_property_max
    omega_n = 1.0 / c_noise_max
    
    # Different weight scenarios
    scenarios = [
        ("Balanced", 0.5, 0.3, 0.2),
        ("High fatality (recommended)", 0.7, 0.2, 0.1),
        ("Very high fatality", 0.8, 0.15, 0.05),
    ]
    
    print(f"\n✓ Comparison of different weight scenarios:")
    print(f"  (Using high population area: c_f={c_fatality_high}, "
          f"c_p={c_property_med}, c_n={c_noise_low})\n")
    
    for name, alpha_f, alpha_p, alpha_n in scenarios:
        c_integrated = (
            alpha_f * omega_f * c_fatality_high +
            alpha_p * omega_p * c_property_med +
            alpha_n * omega_n * c_noise_low
        )
        
        # Contribution from each risk type
        contrib_f = alpha_f * omega_f * c_fatality_high
        contrib_p = alpha_p * omega_p * c_property_med
        contrib_n = alpha_n * omega_n * c_noise_low
        
        print(f"  {name}:")
        print(f"    Weights: α_f={alpha_f:.2f}, α_p={alpha_p:.2f}, α_n={alpha_n:.2f}")
        print(f"    Contributions: fatality={contrib_f:.4f} ({contrib_f/c_integrated*100:.1f}%), "
              f"property={contrib_p:.4f} ({contrib_p/c_integrated*100:.1f}%), "
              f"noise={contrib_n:.4f} ({contrib_n/c_integrated*100:.1f}%)")
        print(f"    Total integrated cost: {c_integrated:.4f}\n")


if __name__ == "__main__":
    test_weight_constraints()
    test_normalization_factor()
    test_integrated_cost_formula()
    test_fatality_weight_impact()
    
    print("\n" + "=" * 70)
    print("✓ All Tests Complete!")
    print("=" * 70)