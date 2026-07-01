"""
Data Configuration for EDA-CostA* Experiments.

This file contains only data path configurations.
For risk model and path planning parameters, see:
    core/risk_model/risk_config.py
"""

from pathlib import Path

# ===== Data Paths =====
# Data directory is located in EDAcostAstar/
BASE_DIR = Path(__file__).resolve().parent / "data"
BUILDINGS_DIR = BASE_DIR / "buildings"
POPULATION_FILE = BASE_DIR / "population" / "population.tif"

# ===== Grid Configuration =====
CELL_SIZE: float = 80.0  # meters
LAYER_ALTITUDES: list[float] = [30.0, 60.0, 90.0, 120.0]  # meters
PADDING: float = 160.0  # meters
TARGET_CRS: str = "EPSG:3857"
