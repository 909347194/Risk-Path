"""
Test Noise Risk Model Implementation

Tests the noise impact risk model based on Eq. 17:
c_noise = L(sl) = wLh / √(h² + d²)
"""

import sys
import numpy as np
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from core.risk_model.noise_risk import NoiseRiskModel
except ImportError:
    # Try relative import
    from ..risk_model.noise_risk import NoiseRiskModel


def test_noise_risk_model():
    """Test the noise risk model implementation."""
    print("=" * 70)
    print("Testing Noise Risk Model (Eq. 17)")
    print("=" * 70)
    
    # Initialize noise risk model
    noise_model = NoiseRiskModel()
    
    # Test height threshold calculation
    h_threshold = noise_model.compute_height_threshold()
    print(f"\n✓ Height threshold calculation:")
    print(f"  - UAV noise level: {noise_model.uav_noise_level_db} dB")
    print(f"  - Threshold level: {noise_model.noise_threshold_db} dB") 
    print(f"  - Calculated threshold height: {h_threshold:.2f} m")
    
    # Test sound level at different altitudes
    print(f"\n✓ Sound level vs altitude:")
    for altitude in [10, 30, 60, 90, 120, 150]:
        sound_level = noise_model.compute_sound_level_at_height(altitude)
        above_threshold = altitude > h_threshold
        status = "ABOVE THRESHOLD" if above_threshold else "BELOW THRESHOLD"
        print(f"  - Altitude {altitude:3d}m: {sound_level:6.2f} dB ({status})")
    
    # Test formula correctness with known values
    print(f"\n✓ Formula verification (Eq. 17):")
    test_altitude = 50.0
    test_distance = 0.0  # Directly below UAV
    
    sound_level_test = noise_model.compute_sound_level_at_height(test_altitude)
    expected_cost = (noise_model.noise_weight * sound_level_test * test_altitude) / np.sqrt(test_altitude**2 + test_distance**2)
    computed_cost = noise_model.compute_noise_cost_formula_17(test_altitude, np.array([test_distance]))[0]
    
    print(f"  - Test case: h={test_altitude}m, d={test_distance}m")
    print(f"  - Expected: w*L*h/√(h²+d²) = {expected_cost:.4f}")
    print(f"  - Computed: {computed_cost:.4f}")
    print(f"  - Match: {'✓ YES' if np.isclose(expected_cost, computed_cost) else '✗ NO'}")
    
    # Test with altitude above threshold
    if h_threshold < 200:  # Only test if threshold is reasonable
        high_altitude = h_threshold + 10
        # Create dummy distance array
        dummy_distances = np.zeros(100)
        noise_cost_high = noise_model.compute_noise_cost_formula_17(high_altitude, dummy_distances)
        noise_cost_thresholded = noise_model.apply_height_threshold(noise_cost_high, high_altitude)
        
        print(f"  - Above threshold ({high_altitude:.1f}m): "
              f"original={noise_cost_high[0]:.6f}, thresholded={noise_cost_thresholded[0]:.6f}")
        
        # Should be all zeros
        if np.allclose(noise_cost_thresholded, 0):
            print("  ✓ CONFIRMED: Noise cost = 0 above threshold height")
        else:
            print("  ⚠ WARNING: Noise cost not zero above threshold")
    
    print("\n" + "=" * 70)
    print("✓ Noise Risk Model Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    test_noise_risk_model()