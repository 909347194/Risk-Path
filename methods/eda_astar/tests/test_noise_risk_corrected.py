"""
Test Corrected Noise Risk Model Implementation

Tests the noise impact risk model based on CORRECTED Eq. 17:
c_noise = L(sl) = ϖ × Lh × [1 / (h² + d²)]

Where:
- ϖ (varpi): Conversion factor from sound intensity to sound level
- Lh: Reference noise produced by drone (55 dB) [55]
- h: Flight altitude (m)
- d: Horizontal distance = 30 feet ≈ 9.144m [54]
"""

import sys
import numpy as np
from pathlib import Path

# Add the risk_model directory to path directly
risk_model_path = Path(__file__).parent.parent / "risk_model"
sys.path.insert(0, str(risk_model_path))

# Import directly without using __init__.py
from noise_risk import NoiseRiskModel


def test_corrected_noise_risk_model():
    """Test the corrected noise risk model implementation."""
    print("=" * 70)
    print("Testing CORRECTED Noise Risk Model (Eq. 17)")
    print("=" * 70)
    
    # Initialize noise risk model
    noise_model = NoiseRiskModel()
    
    print(f"\n✓ Model Parameters:")
    print(f"  - Conversion factor (ϖ): {noise_model.conversion_factor}")
    print(f"  - Reference noise (Lh): {noise_model.reference_noise_db} dB")
    print(f"  - Horizontal distance (d): {noise_model.horizontal_distance_m:.3f} m (30 feet)")
    print(f"  - Threshold: {noise_model.noise_threshold_db} dB")
    
    # Test height threshold calculation
    h_threshold = noise_model.compute_height_threshold()
    print(f"\n✓ Height threshold calculation:")
    print(f"  - Calculated threshold height: {h_threshold:.2f} m")
    print(f"  - Above this height, noise cost = 0")
    
    # Test sound intensity at different altitudes
    print(f"\n✓ Sound Intensity I(si) = 1/(h² + d²):")
    for altitude in [10, 30, 50, 60, 80, 100]:
        intensity = noise_model.compute_sound_intensity(altitude)
        print(f"  - Altitude {altitude:3d}m: I(si) = {intensity:.6e}")
    
    # Test sound level at different altitudes
    print(f"\n✓ Sound Level L(sl) = ϖ × Lh × I(si):")
    for altitude in [10, 30, 50, 60, 80, 100]:
        sound_level = noise_model.compute_sound_level(altitude)
        above_threshold = altitude > h_threshold
        status = "ABOVE THRESHOLD" if above_threshold else "BELOW THRESHOLD"
        print(f"  - Altitude {altitude:3d}m: L(sl) = {sound_level:.4f} dB ({status})")
    
    # Test formula correctness with known values
    print(f"\n✓ Formula verification (Eq. 17):")
    test_altitude = 50.0
    
    # Manual calculation
    d = noise_model.horizontal_distance_m
    expected_intensity = 1.0 / (test_altitude**2 + d**2)
    expected_cost = noise_model.conversion_factor * noise_model.reference_noise_db * expected_intensity
    
    # Computed value
    computed_cost = noise_model.compute_noise_cost_formula_17(test_altitude)[0]
    
    print(f"  - Test case: h={test_altitude}m, d={d:.3f}m")
    print(f"  - I(si) = 1/(h² + d²) = 1/({test_altitude}² + {d:.3f}²) = {expected_intensity:.6e}")
    print(f"  - Expected: ϖ × Lh × I(si) = {noise_model.conversion_factor} × {noise_model.reference_noise_db} × {expected_intensity:.6e}")
    print(f"  - Expected cost: {expected_cost:.6f}")
    print(f"  - Computed cost: {computed_cost:.6f}")
    print(f"  - Match: {'✓ YES' if np.isclose(expected_cost, computed_cost) else '✗ NO'}")
    
    # Test with altitude above threshold
    if h_threshold < 200:  # Only test if threshold is reasonable
        high_altitude = h_threshold + 10
        noise_cost_high = noise_model.compute_noise_cost_formula_17(high_altitude)
        noise_cost_thresholded = noise_model.apply_height_threshold(noise_cost_high, high_altitude)
        
        print(f"\n✓ Above threshold test:")
        print(f"  - Altitude: {high_altitude:.1f}m (threshold: {h_threshold:.2f}m)")
        print(f"  - Original cost: {noise_cost_high[0]:.6f}")
        print(f"  - After threshold: {noise_cost_thresholded[0]:.6f}")
        
        # Should be all zeros
        if np.allclose(noise_cost_thresholded, 0):
            print("  ✓ CONFIRMED: Noise cost = 0 above threshold height")
        else:
            print("  ⚠ WARNING: Noise cost not zero above threshold")
    
    # Compare old vs new formula
    print(f"\n✓ Comparison: OLD vs NEW formula")
    print(f"  OLD (incorrect): c_noise = w × L × h / √(h² + d²)")
    print(f"  NEW (correct):   c_noise = ϖ × Lh × [1 / (h² + d²)]")
    
    test_h = 50.0
    test_d = 9.144
    
    old_formula = 0.6 * 75.0 * test_h / np.sqrt(test_h**2 + test_d**2)
    new_formula = 1.0 * 55.0 / (test_h**2 + test_d**2)
    
    print(f"\n  At h={test_h}m, d={test_d}m:")
    print(f"  - OLD formula result: {old_formula:.4f}")
    print(f"  - NEW formula result: {new_formula:.6f}")
    print(f"  - Difference: {abs(old_formula - new_formula):.4f}")
    
    print("\n" + "=" * 70)
    print("✓ Corrected Noise Risk Model Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_corrected_noise_risk_model()