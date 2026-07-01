"""
Experiment 4: Algorithm Comparison

This experiment compares three path planning algorithms:
1. Standard Cost A* (baseline)
2. Original EDA-A* (Algorithm 1)
3. Two-Stage EDA-CostA* (Algorithm 2, proposed method)

Metrics compared:
- Path cost (total vertex cost)
- Path length (number of waypoints)
- Computation time
- Total distance

Usage:
    cd src/EDAcostAstar
    uv run python experiments/experiment_04_comparison.py
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
from core.path_planning.astar import CostAStarSearcher
from core.path_planning.eda_costastar import EDACostAStarSearcher
from core.path_planning.two_stage_eda_costastar import TwoStageEDACostAStarSearcher
from core.path_planning.enhanced_astar import EnhancedCostAStarSearcher
from config import (
    BUILDINGS_DIR,
    POPULATION_FILE,
    CELL_SIZE,
    LAYER_ALTITUDES,
    PADDING,
)


def run_algorithm_comparison():
    """Run comprehensive algorithm comparison."""
    
    print("=" * 80)
    print("Experiment 4: Algorithm Comparison")
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
    
    # Define start and goal
    start_layer, start_row, start_col = 0, 0, 0
    goal_layer = len(grid.layer_altitudes) - 1
    goal_row = grid.height - 1
    goal_col = grid.width - 1
    
    print(f"\n  Start: layer={start_layer}, row={start_row}, col={start_col}")
    print(f"  Goal:  layer={goal_layer}, row={goal_row}, col={goal_col}")
    
    # ===== Step 4: Run All Three Algorithms =====
    print("\n[4/5] Running algorithm comparison...")
    
    results = {}
    
    # Algorithm 1: Standard Cost A*
    print("\n" + "="*80)
    print("[1/3] Running Standard Cost A*...")
    print("="*80)
    
    start_time = time.time()
    searcher1 = CostAStarSearcher(graph=graph)
    path1 = searcher1.search(
        start_layer=start_layer,
        start_row=start_row,
        start_col=start_col,
        goal_layer=goal_layer,
        goal_row=goal_row,
        goal_col=goal_col,
        cost_map=cost_map,
    )
    time1 = time.time() - start_time
    
    if path1 is not None:
        metrics1 = searcher1.compute_path_metrics(path1, cost_map)
        results['Standard Cost A*'] = {
            'path': path1,
            'cost': float(metrics1['total_cost']),
            'distance': float(metrics1['total_distance']),
            'time': time1,
            'waypoints': len(path1),
        }
        print(f"  ✓ Completed in {time1:.2f}s")
        print(f"    Cost: {metrics1['total_cost']:.2f}, Waypoints: {len(path1)}")
    else:
        print("  ✗ No path found")
    
    # Algorithm 2: Original EDA-A*
    print("\n" + "="*80)
    print("[2/3] Running Original EDA-A*...")
    print("="*80)
    
    start_time = time.time()
    searcher2 = EDACostAStarSearcher(
        graph=graph,
        population_size=20,
        elite_size=4,
        max_generations=30,
        learning_rate=0.2,
    )
    path2 = searcher2.search(
        start_layer=start_layer,
        start_row=start_row,
        start_col=start_col,
        goal_layer=goal_layer,
        goal_row=goal_row,
        goal_col=goal_col,
        cost_map=cost_map,
    )
    time2 = time.time() - start_time
    
    if path2 is not None:
        metrics2 = searcher2.astar_searcher.compute_path_metrics(path2, cost_map)
        results['Original EDA-A*'] = {
            'path': path2,
            'cost': float(metrics2['total_cost']),
            'distance': float(metrics2['total_distance']),
            'time': time2,
            'waypoints': len(path2),
        }
        print(f"  ✓ Completed in {time2:.2f}s")
        print(f"    Cost: {metrics2['total_cost']:.2f}, Waypoints: {len(path2)}")
    else:
        print("  ✗ No path found")
    
    # Algorithm 3: Two-Stage EDA-CostA*
    print("\n" + "="*80)
    print("[3/3] Running Two-Stage EDA-CostA*...")
    print("="*80)
    
    start_time = time.time()
    searcher3 = TwoStageEDACostAStarSearcher(
        graph=graph,
        eda_population_size=20,
        eda_elite_size=4,
        eda_max_generations=30,
        eda_learning_rate=0.2,
        n_clusters=5,
        epsilon=0.2,
    )
    path3 = searcher3.search(
        start_layer=start_layer,
        start_row=start_row,
        start_col=start_col,
        goal_layer=goal_layer,
        goal_row=goal_row,
        goal_col=goal_col,
        cost_map=cost_map,
    )
    time3 = time.time() - start_time
    
    if path3 is not None:
        enhanced_searcher = EnhancedCostAStarSearcher(graph)
        metrics3 = enhanced_searcher.compute_path_metrics(path3, cost_map)
        results['Two-Stage EDA-CostA*'] = {
            'path': path3,
            'cost': float(metrics3['total_cost']),
            'distance': float(metrics3['total_distance']),
            'time': time3,
            'waypoints': len(path3),
        }
        print(f"  ✓ Completed in {time3:.2f}s")
        print(f"    Cost: {metrics3['total_cost']:.2f}, Waypoints: {len(path3)}")
    else:
        print("  ✗ No path found")
    
    # ===== Step 5: Generate Comparison Report =====
    print("\n[5/5] Generating comparison report...")
    
    if not results:
        print("\n✗ No successful results to compare")
        return
    
    print(f"\n{'='*80}")
    print("Comparison Results:")
    print(f"{'='*80}")
    print(f"{'Algorithm':<25} {'Cost':>10} {'Distance(m)':>12} {'Time(s)':>10} {'Waypoints':>10}")
    print("-" * 80)
    
    for algo_name, data in results.items():
        print(f"{algo_name:<25} {data['cost']:>10.2f} {data['distance']:>12.2f} "
              f"{data['time']:>10.2f} {data['waypoints']:>10}")
    
    # Find best algorithm for each metric
    best_cost_algo = min(results.items(), key=lambda x: x[1]['cost'])[0]
    best_time_algo = min(results.items(), key=lambda x: x[1]['time'])[0]
    
    print(f"\n✓ Best cost: {best_cost_algo}")
    print(f"✓ Fastest: {best_time_algo}")
    
    # Save comparison results
    output_dir = project_root / "output" / "experiment_04_comparison"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save summary
    summary_data = {
        'comparison_date': time.strftime('%Y-%m-%d %H:%M:%S'),
        'grid_info': {
            'dimensions': f"{grid.width}x{grid.height}x{len(grid.layer_altitudes)}",
            'cell_size': CELL_SIZE,
            'altitudes': list(grid.layer_altitudes),
        },
        'start': [start_layer, start_row, start_col],
        'goal': [goal_layer, goal_row, goal_col],
        'results': {
            name: {
                'cost': data['cost'],
                'distance': data['distance'],
                'time': data['time'],
                'waypoints': data['waypoints'],
            }
            for name, data in results.items()
        },
        'best_cost_algorithm': best_cost_algo,
        'fastest_algorithm': best_time_algo,
    }
    
    summary_file = output_dir / "comparison_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary_data, f, indent=2)
    print(f"\n✓ Comparison summary saved to: {summary_file}")
    
    # Save individual paths
    for algo_name, data in results.items():
        path_coords = [graph.unpack_index(idx) for idx in data['path']]
        safe_name = algo_name.replace(' ', '_').replace('-', '_')
        path_file = output_dir / f"path_{safe_name}.npy"
        np.save(path_file, np.array(path_coords))
    
    print(f"✓ All paths saved to: {output_dir}")
    
    # ===== Optional: Interactive Comparison Visualization =====
    try:
        from utils.interactive_visualizer import InteractiveVisualizer
        
        print("\n[6/6] Creating interactive comparison visualization...")
        
        viz = InteractiveVisualizer(output_dir=str(output_dir))
        
        # Convert all paths to coordinate tuples
        paths_dict = {}
        for algo_name, data in results.items():
            path_tuples = [tuple(graph.unpack_index(idx)) for idx in data['path']]
            paths_dict[algo_name] = path_tuples
        
        # Create interactive comparison plot
        fig = viz.plot_multiple_paths_interactive(
            paths_dict=paths_dict,
            title="Algorithm Comparison - 3D Paths (Interactive)",
            colors=['blue', 'red', 'green']
        )
        viz.save_figure(fig, "comparison_3d_interactive.html")
        
        print("  ✓ Interactive comparison created")
        print(f"  → Open output/experiment_04_comparison/comparison_3d_interactive.html in browser")
        
    except ImportError:
        print("\n  ⚠ Plotly not installed. Skipping interactive visualization.")
        print("  → Install with: uv add plotly")
    
    print("\n" + "=" * 80)
    print("✓ Experiment 4 Complete!")
    print("=" * 80)


if __name__ == "__main__":
    run_algorithm_comparison()
