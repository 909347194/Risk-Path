"""
Interactive 3D Visualization Demo

This script demonstrates how to use Plotly-based interactive visualization
for path planning results.

Features:
- Interactive 3D path visualization (rotate, zoom, pan)
- Multiple algorithm comparison
- Cost map volume rendering
- EDA convergence history
- Export to HTML for sharing

Usage:
    cd src/EDAcostAstar
    uv run python examples/demo_interactive_visualization.py
"""

import sys
from pathlib import Path
import numpy as np

# Add project root to Python path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from utils.interactive_visualizer import InteractiveVisualizer


def demo_basic_3d_path():
    """Demo 1: Basic interactive 3D path visualization."""
    print("=" * 80)
    print("Demo 1: Basic Interactive 3D Path")
    print("=" * 80)
    
    # Generate sample path
    np.random.seed(42)
    n_points = 50
    path = [
        (i // 15,  # layer
         int(20 + 30 * np.sin(i / 10)),  # row
         int(20 + 30 * np.cos(i / 10)))  # col
        for i in range(n_points)
    ]
    
    # Create visualizer
    viz = InteractiveVisualizer(output_dir="output/demo")
    
    # Create interactive plot
    fig = viz.plot_path_3d_interactive(
        path=path,
        title="Sample 3D Path (Interactive)"
    )
    
    # Save to HTML
    viz.save_figure(fig, "basic_3d_path.html")
    
    # Show in browser (optional)
    print("\n✓ Opening plot in browser...")
    fig.show()
    
    print("\n" + "=" * 80)


def demo_multiple_paths_comparison():
    """Demo 2: Compare multiple paths from different algorithms."""
    print("\n" + "=" * 80)
    print("Demo 2: Multiple Algorithm Comparison")
    print("=" * 80)
    
    # Generate sample paths for different algorithms
    np.random.seed(42)
    n_points = 50
    
    paths_dict = {
        'Standard A*': [
            (i // 15, int(20 + 30 * np.sin(i / 10)), int(20 + 30 * np.cos(i / 10)))
            for i in range(n_points)
        ],
        'Original EDA-A*': [
            (i // 15, int(22 + 28 * np.sin(i / 10 + 0.2)), int(22 + 28 * np.cos(i / 10 + 0.2)))
            for i in range(n_points)
        ],
        'Two-Stage EDA': [
            (i // 15, int(18 + 32 * np.sin(i / 10 - 0.2)), int(18 + 32 * np.cos(i / 10 - 0.2)))
            for i in range(n_points)
        ],
    }
    
    # Create visualizer
    viz = InteractiveVisualizer(output_dir="output/demo")
    
    # Create comparison plot
    fig = viz.plot_multiple_paths_interactive(
        paths_dict=paths_dict,
        title="Algorithm Comparison (Interactive)",
        colors=['blue', 'red', 'green']
    )
    
    # Save to HTML
    viz.save_figure(fig, "algorithm_comparison.html")
    
    print("\n✓ Opening comparison plot in browser...")
    fig.show()
    
    print("\n" + "=" * 80)


def demo_cost_map_volume():
    """Demo 3: Visualize cost map as 3D volume."""
    print("\n" + "=" * 80)
    print("Demo 3: Cost Map Volume Rendering")
    print("=" * 80)
    
    # Generate sample cost map
    np.random.seed(42)
    cost_map = np.random.rand(4, 50, 50) * 10
    
    # Add some structure
    for i in range(4):
        for j in range(50):
            for k in range(50):
                cost_map[i, j, k] += 5 * np.exp(-((j - 25)**2 + (k - 25)**2) / 200)
    
    # Create visualizer
    viz = InteractiveVisualizer(output_dir="output/demo")
    
    # Create volume plot
    fig = viz.plot_cost_map_3d_interactive(
        cost_map=cost_map,
        title="Cost Map Volume (Interactive)",
        colorscale='Viridis'
    )
    
    # Save to HTML
    viz.save_figure(fig, "cost_map_volume.html")
    
    print("\n✓ Opening cost map visualization in browser...")
    fig.show()
    
    print("\n" + "=" * 80)


def demo_eda_convergence():
    """Demo 4: EDA convergence history."""
    print("\n" + "=" * 80)
    print("Demo 4: EDA Convergence History")
    print("=" * 80)
    
    # Generate sample convergence data
    generations = list(range(30))
    best_fitness = [100 * np.exp(-g / 10) + np.random.rand() * 5 for g in generations]
    avg_fitness = [f + np.random.rand() * 10 for f in best_fitness]
    
    convergence_history = [
        {
            'generation': g,
            'best_fitness': bf,
            'avg_fitness': af
        }
        for g, bf, af in zip(generations, best_fitness, avg_fitness)
    ]
    
    # Create visualizer
    viz = InteractiveVisualizer(output_dir="output/demo")
    
    # Create convergence plot
    fig = viz.plot_eda_convergence_interactive(
        convergence_history=convergence_history,
        title="EDA Convergence (Interactive)"
    )
    
    # Save to HTML
    viz.save_figure(fig, "eda_convergence.html")
    
    print("\n✓ Opening convergence plot in browser...")
    fig.show()
    
    print("\n" + "=" * 80)


def demo_complete_dashboard():
    """Demo 5: Complete experiment dashboard."""
    print("\n" + "=" * 80)
    print("Demo 5: Complete Experiment Dashboard")
    print("=" * 80)
    
    # Generate sample data
    np.random.seed(42)
    n_points = 50
    path = [
        (i // 15, int(20 + 30 * np.sin(i / 10)), int(20 + 30 * np.cos(i / 10)))
        for i in range(n_points)
    ]
    
    cost_map = np.random.rand(4, 50, 50) * 10
    
    generations = list(range(30))
    best_fitness = [100 * np.exp(-g / 10) + np.random.rand() * 5 for g in generations]
    convergence_history = [
        {'generation': g, 'best_fitness': bf}
        for g, bf in zip(generations, best_fitness)
    ]
    
    # Create visualizer
    viz = InteractiveVisualizer(output_dir="output/demo")
    
    # Create dashboard
    fig = viz.create_dashboard(
        path=path,
        cost_map=cost_map,
        convergence_history=convergence_history,
        title="Complete Experiment Dashboard"
    )
    
    # Save to HTML
    viz.save_figure(fig, "complete_dashboard.html")
    
    print("\n✓ Opening dashboard in browser...")
    fig.show()
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("Interactive 3D Visualization Demo")
    print("=" * 80)
    print("\nThis demo will create several interactive plots and open them in your browser.")
    print("You can rotate, zoom, and pan the 3D views!")
    print("=" * 80 + "\n")
    
    try:
        # Run all demos
        demo_basic_3d_path()
        demo_multiple_paths_comparison()
        demo_cost_map_volume()
        demo_eda_convergence()
        demo_complete_dashboard()
        
        print("\n" + "=" * 80)
        print("✓ All demos completed!")
        print("=" * 80)
        print(f"\nHTML files saved to: output/demo/")
        print("\nYou can:")
        print("  1. Open the HTML files in any modern browser")
        print("  2. Share them with collaborators")
        print("  3. Embed them in web pages or reports")
        print("=" * 80)
        
    except ImportError as e:
        print(f"\n✗ Error: {e}")
        print("\nPlotly is required for interactive visualization.")
        print("Install it with: uv add plotly")
        print("=" * 80)
