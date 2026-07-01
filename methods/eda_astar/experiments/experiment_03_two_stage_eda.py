"""
Experiment 3: Two-Stage EDA-CostA* Algorithm (Algorithm 2 & 3)

This experiment validates the proposed Two-Stage EDA-CostA* algorithm.
It combines EDA optimization with K-means clustering and adaptive heuristics.

Algorithm Stages:
  Stage 1: EDA Optimization - Optimize searching region
  Stage 2: Clustering - Apply K-means to extract open points
  Stage 3: Heuristic Computation - Calculate h_Dist and h_Drctn
  Stage 4: Enhanced A* - Run with adaptive heuristic switching

Key Contributions:
  - Advanced heuristics (Eq. 24-25)
  - Adaptive switching mechanism (Eq. 26)
  - Cluster-based path guidance

Usage:
    cd src/EDAcostAstar
    uv run python experiments/experiment_03_two_stage_eda.py
"""

import sys
from pathlib import Path
import time
import json
import numpy as np

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from core.risk_model.grid_model import Grid3D, load_building_shapefiles
from core.risk_model.cost_model import IntegratedCostModel
from core.path_planning.graph import Grid3DPathGraph
from core.path_planning.two_stage_eda_costastar import TwoStageEDACostAStarSearcher
from config import (
    BUILDINGS_DIR,
    POPULATION_FILE,
    CELL_SIZE,
    LAYER_ALTITUDES,
    PADDING,
)


def run_two_stage_eda_experiment():
    """Run Two-Stage EDA-CostA* experiment."""
    
    print("=" * 80)
    print("Experiment 3: Two-Stage EDA-CostA* Algorithm (Algorithm 2)")
    print("=" * 80)
    
    # ===== Step 1: Load Data and Create Grid =====
    print("\n[1/5] Loading data and creating grid...")
    
    try:
        buildings = load_building_shapefiles(BUILDINGS_DIR)
        print(f"  ✓ Loaded {len(buildings)} buildings")
    except Exception as e:
        print(f"  ✗ Failed to load buildings: {e}")
        return
    
    # Create grid from data sources
    grid = Grid3D.from_sources(
        buildings=buildings,
        population_raster=POPULATION_FILE,
        cell_size=CELL_SIZE,
        padding=PADDING,
    )
    print(f"  ✓ Grid created: {grid.summary()}")
    
    # ===== Step 2: Compute Cost Map =====
    print("\n[2/5] Computing integrated cost map...")
    
    cost_model = IntegratedCostModel(
        grid=grid,
        population_raster=POPULATION_FILE,
        buildings=buildings,
        alpha_fatality=0.7,
        alpha_property=0.2,
        alpha_noise=0.1,
    )
    
    results = cost_model.compute_integrated_costs()
    cost_map = results['integrated_costs']
    print(f"  ✓ Cost map computed: shape={cost_map.shape}")
    print(f"  ✓ Cost range: [{cost_map.min():.2f}, {cost_map.max():.2f}]")
    
    # ===== Step 3: Build Graph =====
    print("\n[3/5] Building 3D path graph...")
    
    graph = Grid3DPathGraph(grid=grid)
    print(f"  ✓ Graph built with {graph.node_count} nodes")
    
    # ===== Step 4: Run Two-Stage EDA-CostA* =====
    print("\n[4/5] Running Two-Stage EDA-CostA* search...")
    
    searcher = TwoStageEDACostAStarSearcher(
        graph=graph,
        eda_population_size=20,
        eda_elite_size=4,
        eda_max_generations=30,
        eda_learning_rate=0.2,
        n_clusters=5,
        epsilon=0.2,
    )
    
    # Define start and goal
    start_layer, start_row, start_col = 0, 0, 0
    goal_layer = len(grid.layer_altitudes) - 1
    goal_row = grid.height - 1
    goal_col = grid.width - 1
    
    print(f"  Start: layer={start_layer}, row={start_row}, col={start_col}")
    print(f"  Goal:  layer={goal_layer}, row={goal_row}, col={goal_col}")
    
    start_time = time.time()
    path = searcher.search(
        start_layer=start_layer,
        start_row=start_row,
        start_col=start_col,
        goal_layer=goal_layer,
        goal_row=goal_row,
        goal_col=goal_col,
        cost_map=cost_map,
        risk_weight=1.0,
        distance_weight=1.0,
    )
    elapsed_time = time.time() - start_time
    
    # ===== Step 5: Analyze Results =====
    print("\n[5/5] Analyzing results...")
    
    if path is None:
        print("\n✗ FAILED: No path found!")
        return
    
    print(f"\n{'='*80}")
    print("Results:")
    print(f"{'='*80}")
    print(f"  ✓ Path found with {len(path)} waypoints")
    print(f"  ✓ Computation time: {elapsed_time:.2f}s")
    
    # Compute path metrics
    from core.path_planning.enhanced_astar import EnhancedCostAStarSearcher
    enhanced_searcher = EnhancedCostAStarSearcher(graph)
    metrics = enhanced_searcher.compute_path_metrics(path, cost_map)
    print(f"  ✓ Total vertex cost: {metrics['total_cost']:.2f}")
    print(f"  ✓ Total distance: {metrics['total_distance']:.2f} m")
    print(f"  ✓ Average cost per node: {metrics['avg_cost_per_node']:.2f}")
    
    # Save results
    output_dir = project_root / "output" / "experiment_03"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    result_data = {
        'algorithm': 'Two-Stage EDA-CostA*',
        'path_length': len(path),
        'total_cost': float(metrics['total_cost']),
        'total_distance': float(metrics['total_distance']),
        'computation_time': elapsed_time,
        'two_stage_params': {
            'eda_population_size': searcher.eda_searcher.population_size,
            'eda_elite_size': searcher.eda_searcher.elite_size,
            'eda_max_generations': searcher.eda_searcher.max_generations,
            'n_clusters': searcher.n_clusters,
            'epsilon': searcher.epsilon,
        },
        'grid_info': {
            'dimensions': f"{grid.width}x{grid.height}x{len(grid.layer_altitudes)}",
            'cell_size': CELL_SIZE,
            'altitudes': list(grid.layer_altitudes),
        },
        'start': [start_layer, start_row, start_col],
        'goal': [goal_layer, goal_row, goal_col],
    }
    
    result_file = output_dir / "results.json"
    with open(result_file, 'w') as f:
        json.dump(result_data, f, indent=2)
    print(f"\n✓ Results saved to: {result_file}")
    
    # Save path coordinates
    path_coords = [graph.unpack_index(node_idx) for node_idx in path]
    path_file = output_dir / "path.npy"
    np.save(path_file, np.array(path_coords))
    print(f"✓ Path coordinates saved to: {path_file}")
    
    print("\n" + "=" * 80)
    print("✓ Experiment 3 Complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_two_stage_eda_experiment()
