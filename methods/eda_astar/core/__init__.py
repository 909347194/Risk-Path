"""
EDA-CostA* Path Planning Package - Core Modules

This package implements the Two-Stage EDA-CostA* algorithm for UAV path planning
in urban environments with integrated risk assessment.

Reference: Pang et al. (2022) - Hybrid EDA-A* algorithm for cost-based path planning
"""

# Version
__version__ = "1.0.0"

# ============================================================================
# Path Planning Core
# ============================================================================
from .path_planning.graph import Grid3DPathGraph
from .path_planning.astar import CostAStarSearcher
from .path_planning.enhanced_astar import EnhancedCostAStarSearcher
from .path_planning.eda_costastar import EDACostAStarSearcher
from .path_planning.two_stage_eda_costastar import TwoStageEDACostAStarSearcher
from .path_planning.clustering import KMeansClusterer
from .path_planning.heuristic_calculator import AdvancedHeuristicCalculator

# ============================================================================
# Risk Model Core
# ============================================================================
from .risk_model.base_risk import BaseRiskModel
from .risk_model.fatality_risk import FatalityRiskModel
from .risk_model.traffic_risk import TrafficRiskModel
from .risk_model.property_risk import PropertyDamageRiskModel
from .risk_model.noise_risk import NoiseRiskModel
from .risk_model.cost_model import IntegratedCostModel
from .risk_model.grid_model import Grid3D, load_building_shapefiles
from .risk_model.population_density import PopulationDensityModel
from .risk_model.risk_config import (
    RISK_WEIGHTS,
    UAV_MASS,
    UAV_CRASH_PROBABILITY,
)

# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Path Planning
    'Grid3DPathGraph',
    'CostAStarSearcher',
    'EnhancedCostAStarSearcher',
    'EDACostAStarSearcher',
    'TwoStageEDACostAStarSearcher',
    'KMeansClusterer',
    'AdvancedHeuristicCalculator',
    
    # Risk Models
    'BaseRiskModel',
    'FatalityRiskModel',
    'TrafficRiskModel',
    'PropertyDamageRiskModel',
    'NoiseRiskModel',
    'IntegratedCostModel',
    'Grid3D',
    'PopulationDensityModel',
    
    # Configuration
    'RISK_WEIGHTS',
    'UAV_MASS',
    'UAV_CRASH_PROBABILITY',
]
