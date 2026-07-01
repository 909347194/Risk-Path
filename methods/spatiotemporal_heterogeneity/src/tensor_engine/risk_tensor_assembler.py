"""
Risk Tensor Assembler — bridge from data_provision outputs to EnvTensor inputs.

Converts aligned 2D/3D NumPy matrices (from DataPipeline) into the four 4D risk
tensors that the algorithm layer consumes via EnvTensor.

Usage:
    from data_provision.pipeline import DataPipeline
    from tensor_engine.risk_tensor_assembler import build_risk_tensors
    from algorithms.env_tensor import EnvTensor

    pipeline = DataPipeline(data_type='synthetic')
    result = pipeline.run_all()
    tensors = build_risk_tensors(result, grid=pipeline.grid)
    env_tensor = EnvTensor(**tensors, grid=pipeline.grid)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np

from .grid_system import GridSystem
from .dynamic_p_crash import DynamicCrashProbability
from .dynamic_fatality import DynamicFatalityModel
from .static_obstacle import PropertyDamageModel
from .dynamic_noise import get_micro_grid_noise_model


def build_risk_tensors(
    pipeline_result,
    grid: GridSystem,
    flight_altitude: float = 50.0,
    config_path: Optional[Union[str, Path]] = None,
) -> Dict[str, np.ndarray]:
    """
    Assemble the four risk tensors from DataPipeline outputs.

    Follows the data flow: data_provision (aligned matrices) →
    tensor_engine (risk models) → four 4D risk tensors for EnvTensor.

    Args:
        pipeline_result: PipelineResult from DataPipeline.run_all(), or any
            object with attributes: landuse, building_heights, rho_population,
            rho_vehicle, wind_field, rain_data.
        grid: GridSystem instance (must match the pipeline's grid).
        flight_altitude: UAV flight altitude (m) for risk calculations.
        config_path: Path to common.yaml. If None, uses project default.

    Returns:
        Dict with keys 'p_crash', 'fatality', 'property', 'noise',
        each a numpy array ready for EnvTensor construction.
    """
    nx, ny, nz, nt = grid.shape

    if config_path is None:
        project_dir = Path(__file__).resolve().parents[2]
        config_path = project_dir / "configs" / "common.yaml"

    # Extract pipeline outputs
    landuse = pipeline_result.landuse
    building = pipeline_result.building_heights
    rho_pop = pipeline_result.rho_population
    rho_vehicle = pipeline_result.rho_vehicle
    wind = pipeline_result.wind_field
    rain = pipeline_result.rain_data

    # --- 1. Crash probability: P_crash(x,y,z,t) ---
    crash_model = DynamicCrashProbability(config_path=str(config_path))
    wind_3d = wind[:, :, np.newaxis, :]  # (nx,ny,1,nt) → broadcast to nz
    rain_3d = rain[:, :, np.newaxis, :]
    f_wind = crash_model.compute_wind_factor(wind_3d)
    f_rain = crash_model.compute_rain_factor(rain_3d)
    f_obs = np.ones((nx, ny, nz, nt), dtype=np.float32)  # placeholder
    p_crash = crash_model.compute_pcrash(
        f_wind, f_rain, f_obs, dt=grid.temporal.dt_minutes * 60.0
    )
    p_crash = np.clip(p_crash, 0.0, 1.0).astype(np.float32)

    # --- 2. Fatality consequence: E_fatality(x,y,z,t) ---
    fatality_model = DynamicFatalityModel(config_path=config_path)
    e_fatality_2d = fatality_model.compute_fatality_consequence(
        rho_pop=rho_pop, rho_vehicle=rho_vehicle, flight_altitude=flight_altitude,
    )  # (nx, ny, nt)
    e_fatality = np.broadcast_to(
        e_fatality_2d[:, :, np.newaxis, :], (nx, ny, nz, nt)
    ).astype(np.float32)

    # --- 3. Property consequence: E_property(x,y) ---
    prop_model = PropertyDamageModel(
        building_heights=building, config_path=str(config_path),
    )
    e_property = prop_model.compute_property_consequence(
        flight_altitude=flight_altitude,
    ).astype(np.float32)

    # --- 4. Noise cost: r_noise(x,y,z,t) ---
    noise_model = get_micro_grid_noise_model(grid=grid, config_path=str(config_path))
    r_noise = noise_model.compute_noise_cost(
        landuse=landuse, population_density=rho_pop, flight_altitude=flight_altitude,
    ).astype(np.float32)

    return {
        "p_crash": p_crash,
        "fatality": e_fatality,
        "property": e_property,
        "noise": r_noise,
    }
