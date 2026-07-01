"""
Third-Party Fatality Risk Model

Implements fatality risk assessment for UAV crashes based on:
- Pedestrian fatalities (Eq. 2-8)
- Vehicle occupant fatalities (Eq. 9)
- Total fatality risk (Eq. 1)

Based on: Pang et al. (2022) - Section 3.1.1, Eq. 1-9
"""

from __future__ import annotations

import numpy as np
from typing import Dict, Any, Optional

try:
    from .base_risk import BaseRiskModel
    from .risk_config import UAV_MASS, UAV_IMPACT_AREA, UAV_DRAG_COEFFICIENT
    from .risk_config import UAV_CRASH_PROBABILITY, FATALITY_RISK
except ImportError:
    from base_risk import BaseRiskModel
    from risk_config import UAV_MASS, UAV_IMPACT_AREA, UAV_DRAG_COEFFICIENT
    from risk_config import UAV_CRASH_PROBABILITY, FATALITY_RISK


class FatalityRiskModel(BaseRiskModel):
    """Third-party fatality risk model for UAV crashes.
    
    Computes two components:
    1. Pedestrian fatality risk (c_r_p): Risk to people on ground
    2. Vehicle occupant fatality risk (c_r_v): Risk to people in vehicles
    
    Total fatality risk: c_r_f = c_r_p + c_r_v (Eq. 1)
    
    Key Equations:
    - Eq. 2: c_r_p = P_crash * N_hit^p * R_f^p
    - Eq. 3: N_hit^p = S_hit * σ_p
    - Eq. 4: Fatality probability based on impact energy
    - Eq. 5: E_imp = 0.5 * m * v²
    - Eq. 6-8: UAV fall velocity with air drag
    - Eq. 9: c_r_v = P_crash * N_hit^v * R_f^v
    """
    
    def __init__(self, parameters: Dict[str, Any] = None):
        """
        Args:
            parameters: Fatality risk parameters (uses defaults if None)
        """
        super().__init__(name='fatality', parameters=parameters)
    
    def get_default_parameters(self) -> Dict[str, Any]:
        """Default fatality risk parameters from paper."""
        return {
            'uav_mass': UAV_MASS,
            'uav_impact_area': UAV_IMPACT_AREA,
            'uav_drag_coefficient': UAV_DRAG_COEFFICIENT,
            'crash_probability': UAV_CRASH_PROBABILITY,
            **FATALITY_RISK,
        }
    
    def validate_parameters(self) -> bool:
        """Validate fatality risk parameters."""
        required_params = [
            'uav_mass', 'uav_impact_area', 'crash_probability',
            'alpha', 'beta', 'air_density', 'gravity',
            'fatality_rate_pedestrian', 'fatality_rate_vehicle'
        ]
        
        for param in required_params:
            if param not in self.parameters:
                raise ValueError(f"Missing required parameter: {param}")
            
            value = self.parameters[param]
            if not isinstance(value, (int, float)):
                raise ValueError(f"Parameter {param} must be numeric, got {type(value)}")
            
            if value < 0:
                raise ValueError(f"Parameter {param} must be non-negative, got {value}")
        
        return True
    
    def compute_impact_velocity(
        self,
        altitude: float,
        uav_mass: Optional[float] = None,
        impact_area: Optional[float] = None,
        drag_coeff: Optional[float] = None,
        air_density: Optional[float] = None,
        gravity: Optional[float] = None,
    ) -> float:
        """Compute UAV impact velocity when hitting ground (Eq. 8).
        
        v = sqrt(2mg / (R_l * S_hit * ρ_A) * (1 - exp(-h * R_l * S_hit * ρ_A / m)))
        
        Args:
            altitude: UAV altitude above ground (meters)
            uav_mass: UAV mass (kg), uses default if None
            impact_area: Impact area (m²), uses default if None
            drag_coeff: Drag coefficient R_l, uses default if None
            air_density: Air density ρ_A (kg/m³), uses default if None
            gravity: Gravitational acceleration g (m/s²), uses default if None
            
        Returns:
            Impact velocity (m/s)
        """
        m = uav_mass or self.parameters['uav_mass']
        S_hit = impact_area or self.parameters['uav_impact_area']
        R_l = drag_coeff or self.parameters['uav_drag_coefficient']
        rho_A = air_density or self.parameters['air_density']
        g = gravity or self.parameters['gravity']
        
        # Eq. 8: Velocity with air drag
        # v = sqrt(2mg / (R_l * S_hit * rho_A) * (1 - exp(-h * R_l * S_hit * rho_A / m)))
        
        # Terminal velocity component
        v_terminal_sq = (2 * m * g) / (R_l * S_hit * rho_A)
        
        # Exponential decay component
        exp_arg = -(altitude * R_l * S_hit * rho_A) / m
        
        # Final velocity
        v = np.sqrt(v_terminal_sq * (1 - np.exp(exp_arg)))
        
        return v
    
    def compute_impact_energy(
        self,
        altitude: float,
        uav_mass: Optional[float] = None,
        **kwargs
    ) -> float:
        """Compute impact kinetic energy (Eq. 5).
        
        E_imp = 0.5 * m * v²
        
        Args:
            altitude: UAV altitude (meters)
            uav_mass: UAV mass (kg)
            **kwargs: Additional parameters for velocity computation
            
        Returns:
            Impact energy (Joules)
        """
        m = uav_mass or self.parameters['uav_mass']
        v = self.compute_impact_velocity(altitude, uav_mass=m, **kwargs)
        
        # Eq. 5: Kinetic energy
        E_imp = 0.5 * m * v**2
        
        return E_imp
    
    def compute_fatality_probability(
        self,
        impact_energy: float,
        alpha: Optional[float] = None,
        beta: Optional[float] = None,
    ) -> float:
        """Compute fatality probability based on impact energy (Eq. 4).
        
        S_c = 1 / (1 + sqrt(α/β) * (β/E_imp)^(1/(4*S_c)))
        
        This is implicit equation, solved iteratively.
        
        Args:
            impact_energy: Impact kinetic energy E_imp (Joules)
            alpha: Energy for 50% fatality (Joules)
            beta: Minimum energy threshold (Joules)
            
        Returns:
            Fatality probability S_c (0 to 1)
        """
        alpha = alpha or self.parameters['alpha']
        beta = beta or self.parameters['beta']
        
        # Avoid division by zero
        if impact_energy <= 0:
            return 0.0
        
        if impact_energy < beta:
            return 0.0  # Below threshold, no fatality
        
        # Solve implicit equation iteratively
        # Start with initial guess
        S_c = 0.5
        
        for _ in range(20):  # Iterate to converge
            exponent = 1.0 / (4.0 * S_c)
            term = np.sqrt(alpha / beta) * (beta / impact_energy) ** exponent
            S_c_new = 1.0 / (1.0 + term)
            
            # Check convergence
            if abs(S_c_new - S_c) < 1e-6:
                break
            
            S_c = S_c_new
        
        return S_c
    
    def compute_pedestrian_risk(
        self,
        population_density: np.ndarray,
        altitude: float,
    ) -> np.ndarray:
        """Compute pedestrian fatality risk (Eq. 2-3).
        
        c_r_p = P_crash * N_hit^p * R_f^p
        N_hit^p = S_hit * σ_p
        
        Args:
            population_density: Population density map (people/m² or people/km²)
            altitude: UAV flight altitude (meters)
            
        Returns:
            Pedestrian fatality risk map (fatalities per flight hour)
        """
        # Get parameters
        P_crash = self.parameters['crash_probability']
        S_hit = self.parameters['uav_impact_area']
        R_f_p = self.parameters['fatality_rate_pedestrian']
        shelter_factor = self.parameters.get('shelter_factor', 1.0)
        
        # Compute impact energy and fatality probability
        E_imp = self.compute_impact_energy(altitude)
        S_c = self.compute_fatality_probability(E_imp)
        
        # Eq. 3: Expected number of people hit
        # N_hit^p = S_hit * σ_p * S_c (with fatality probability)
        # Apply shelter factor (buildings provide protection)
        N_hit_p = S_hit * population_density * S_c * shelter_factor
        
        # Eq. 2: Pedestrian fatality risk cost
        c_r_p = P_crash * N_hit_p * R_f_p
        
        return c_r_p
    
    def compute_vehicle_risk(
        self,
        population_density: np.ndarray,
        altitude: float,
    ) -> np.ndarray:
        """Compute vehicle occupant fatality risk (Eq. 9).
        
        c_r_v = P_crash * N_hit^v * R_f^v
        
        Simplified: assumes vehicle density proportional to population density.
        
        Args:
            population_density: Population density map
            altitude: UAV flight altitude (meters)
            
        Returns:
            Vehicle occupant fatality risk map
        """
        # Get parameters
        P_crash = self.parameters['crash_probability']
        R_f_v = self.parameters['fatality_rate_vehicle']
        avg_occupancy = self.parameters.get('avg_vehicle_occupancy', 1.5)
        shelter_factor = self.parameters.get('shelter_factor', 1.0)
        
        # Estimate vehicle density from population density
        # (simplified assumption - can be improved with actual traffic data)
        vehicle_density = population_density / avg_occupancy
        
        # Compute impact energy and fatality probability
        E_imp = self.compute_impact_energy(altitude)
        S_c = self.compute_fatality_probability(E_imp)
        
        # Expected number of vehicle occupants hit
        S_hit = self.parameters['uav_impact_area']
        N_hit_v = S_hit * vehicle_density * S_c * shelter_factor
        
        # Eq. 9: Vehicle occupant fatality risk cost
        c_r_v = P_crash * N_hit_v * R_f_v
        
        return c_r_v
    
    def compute_risk(
        self,
        grid,
        data: Dict[str, Any],
        altitude_override: Optional[float] = None,
        **kwargs
    ) -> np.ndarray:
        """Compute total fatality risk (Eq. 1).
        
        c_r_f = c_r_p + c_r_v
        
        Args:
            grid: Grid3D object (not used, altitude from data or override)
            data: Dictionary containing:
                  - 'population_density': 2D array (people per unit area)
            altitude_override: Fixed altitude for all cells (meters)
                              If None, uses first layer altitude from grid
            **kwargs: Additional parameters
        
        Returns:
            Fatality risk map (2D array: fatalities per flight hour per cell)
        """
        # Get population density
        if 'population_density' not in data:
            raise ValueError("data must contain 'population_density'")
        
        pop_density = data['population_density']
        
        # Determine altitude
        if altitude_override is not None:
            altitude = altitude_override
        else:
            # Use first layer altitude as default
            altitude = grid.layer_altitudes[0]
        
        # Compute pedestrian risk
        c_r_p = self.compute_pedestrian_risk(pop_density, altitude)
        
        # Compute vehicle risk
        c_r_v = self.compute_vehicle_risk(pop_density, altitude)
        
        # Eq. 1: Total fatality risk
        c_r_f = c_r_p + c_r_v
        
        return c_r_f
