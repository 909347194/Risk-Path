"""
Algorithm integration smoke example.

This script demonstrates the algorithm-layer contract:
data_provision/tensor_engine produce component tensors, EnvTensor validates and
broadcasts them, and AStar4D searches on the resulting 4D risk field.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np

try:
    from ..tensor_engine.grid_system import GridSystem, get_micro_grid
    from ..tensor_engine.load_config import load_all_configs
    from .env_tensor import EnvTensor
    from .a_star.astar_4d import AStar4D
except ImportError:  # Allows: python src/algorithms/integration_example.py
    import sys

    ROOT = Path(__file__).resolve().parents[4]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import GridSystem, get_micro_grid
    from methods.spatiotemporal_heterogeneity.src.tensor_engine.load_config import load_all_configs
    from methods.spatiotemporal_heterogeneity.src.algorithms.env_tensor import EnvTensor
    from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D


def build_demo_components(grid: GridSystem, seed: int = 42) -> Dict[str, np.ndarray]:
    """Create deterministic component tensors with shapes used by tensor_engine."""
    rng = np.random.default_rng(seed)
    nx, ny, nz, nt = grid.shape

    p_crash = rng.random((nx, ny, nz, nt), dtype=np.float32) * 1e-5
    fatality = rng.random((nx, ny, nt), dtype=np.float32) * 1e-4
    property_risk = rng.random((nx, ny), dtype=np.float32) * 1e-3
    noise = rng.random((nx, ny, nz, nt), dtype=np.float32) * 1e-4
    obstacle = np.zeros((nx, ny, nz), dtype=np.float32)

    # A small blocked block to prove obstacle propagation without closing the map.
    obstacle[nx // 3 : nx // 3 + 3, ny // 3 : ny // 3 + 3, :] = 1.0

    return {
        "p_crash": p_crash,
        "fatality": fatality,
        "property": property_risk,
        "noise": noise,
        "obstacle": obstacle,
    }


def build_planner_config(configs: Dict[str, Any]) -> Dict[str, float]:
    """Map project YAML conventions to the flat keys consumed by AStar4D."""
    env_config = configs.get("env_config", {})
    cost_config = configs.get("cost_weight", {})

    default_weights = cost_config.get("default", {}) if isinstance(cost_config, dict) else {}
    flight = env_config.get("flight_parameters", {}) if isinstance(env_config, dict) else {}
    uav_constraints = flight.get("uav_constraints", {}) if isinstance(flight, dict) else {}

    return {
        "uav_speed": float(flight.get("cruise_speed", 10.0)),
        "w_distance": float(default_weights.get("w_ops", 0.4)),
        "w_fatality": float(default_weights.get("w_fatal", 1.0)),
        "w_property": float(default_weights.get("w_prop", 1.0)),
        "w_noise": float(default_weights.get("w_noise", 1.0)),
        "survival_threshold": 0.95,
        "max_battery_time": 3600.0,
        "max_climb_rate": float(uav_constraints.get("max_climb_rate", 5.0)),
        "max_descent_rate": float(uav_constraints.get("max_descent_rate", 5.0)),
        "max_labels_per_cell": 4,
    }


def run_path_planning_example() -> Dict[str, Any]:
    """Run the integration smoke example."""
    project_dir = Path(__file__).resolve().parents[2]
    configs = load_all_configs(project_dir / "configs")

    grid = get_micro_grid()
    components = build_demo_components(grid)
    env_tensor = EnvTensor(
        p_crash=components["p_crash"],
        fatality=components["fatality"],
        property=components["property"],
        noise=components["noise"],
        obstacle=components["obstacle"],
        grid=grid,
    )

    planner = AStar4D(grid, env_tensor, build_planner_config(configs))
    start = (2, 2, 5, 0)
    goal = (grid.spatial.nx - 3, grid.spatial.ny - 3, 5)
    result = planner.search(start, goal)

    print(env_tensor.summary())
    print(f"status: {result['status']}")
    if result["status"] == "success":
        print(f"path waypoints: {len(result['path'])}")
        print(f"distance_m: {result['total_distance']:.2f}")
        print(f"flight_time_s: {result['total_time']:.2f}")
        print(f"survival: {result['final_p_survival']:.6f}")
        print(f"objective_cost: {result['objective_cost']:.6f}")
    else:
        print(f"reason: {result.get('reason', 'unknown')}")
    return result


if __name__ == "__main__":
    run_path_planning_example()
