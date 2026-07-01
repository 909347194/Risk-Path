"""
Risk Model Configuration

Centralized configuration for all risk model parameters.
Based on Pang et al. (2022) paper specifications.
"""

from typing import Dict, Any

# ========== UAV Physical Parameters ==========
UAV_MASS = 25.0  # kg (typical delivery UAV)
UAV_IMPACT_AREA = 0.5  # m² (crash impact area S_hit)
UAV_DRAG_COEFFICIENT = 1.0  # R_l (drag coefficient, depends on UAV type)
UAV_CRASH_PROBABILITY = 3.42*1e-4  # P_crash (crashes per flight hour)

# ========== Fatality Risk Parameters (Eq. 1-9) ==========
FATALITY_RISK: Dict[str, Any] = {
    # Impact energy parameters (Eq. 4)
    'alpha': 1e6,  # J (energy causing 50% fatality)
    'beta': 100.0,  # J (minimum energy threshold for fatality)
    
    # Environmental parameters
    'air_density': 1.225,  # kg/m³ (ρ_A at sea level)
    'gravity': 9.8,  # m/s² (g)
    
    # Fatality rate parameters
    'fatality_rate_pedestrian': 1.0,  # R_f^p (pedestrian fatality rate)
    'fatality_rate_vehicle': 1.0,  # R_f^v (vehicle occupant fatality rate)
    
    # Vehicle occupancy
    'avg_vehicle_occupancy': 1.5,  # persons per vehicle
    
    # Population shelter factor (building protection)
    'shelter_factor': 0.3,  # reduction factor when indoors
}

# ========== Property Damage Risk Parameters ==========
# TODO: Add when you provide Eq. 7-9
PROPERTY_RISK: Dict[str, Any] = {
    'building_value_per_m2': 10000.0,  # CNY/m² (example value)
    'damage_coefficient': 1.0,  # damage scaling factor
}

# ========== Noise Impact Parameters ==========
# Based on Eq. 17: c_noise = L(sl) = ϖ × Lh × [1 / (h² + d²)]
NOISE_RISK: Dict[str, Any] = {
    'conversion_factor': 1.0,  # ϖ (varpi): conversion factor from sound intensity to sound level
    'reference_noise_db': 55.0,  # Lh: reference noise produced by drone (dB) [55]
    'horizontal_distance_m': 9.144,  # d: horizontal distance = 30 feet ≈ 9.144m [54]
    'noise_threshold_db': 40.0,  # Threshold noise level (dB) - above this height, no cost [56,57]
}

# ========== Traffic Density Risk Parameters ==========
TRAFFIC_RISK: Dict[str, Any] = {
    'sigma_v_avg': 7120.0,  # average traffic density (from road_density.py)
    'radius': 1.0,  # km (attraction radius, Eq. 12)
}

# ========== Risk Integration Parameters ==========
# Weight factors for combining different risks (must sum to 1.0)
# α_τ: weight factor for risk type τ
RISK_WEIGHTS: Dict[str, float] = {
    'alpha_fatality': 0.5,   # α_1: fatality risk weight (highest priority)
    'alpha_property': 0.3,   # α_2: property damage weight
    'alpha_noise': 0.2,      # α_3: noise impact weight
}

# Note: α_1 + α_2 + α_3 must equal 1.0
# To increase fatality cost weight (as suggested in paper):
# - Increase alpha_fatality (e.g., 0.6 or 0.7)
# - Decrease alpha_property and/or alpha_noise accordingly

# Normalization Method
# ω_τ = 1 / c_τ_max (computed automatically for each layer)
NORMALIZATION_METHOD = 'max'  # Divide by maximum cost value
