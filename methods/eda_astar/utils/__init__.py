"""
Visualization Utilities for EDA-CostA* Experiments

This package provides reusable visualization tools for path planning results,
EDA convergence, clustering, and algorithm comparison.

Available Modules:
    - visualizer: Unified interface (recommended)
    - path_visualizer: Single algorithm visualization (Matplotlib)
    - interactive_visualizer: Interactive 3D visualization (Plotly)
    - comparison_visualizer: Multi-algorithm comparison
    - road_density: Traffic density calculation utility

Usage:
    # Recommended: Use unified interface
    from utils.visualizer import PathVisualizer, ComparisonVisualizer
    
    # Or import specific modules
    from utils.path_visualizer import PathVisualizer
    from utils.interactive_visualizer import InteractiveVisualizer
    from utils.comparison_visualizer import ComparisonVisualizer
    from utils.road_density import calculate_traffic_density
"""

from .visualizer import PathVisualizer, ComparisonVisualizer
from .interactive_visualizer import InteractiveVisualizer

__all__ = ['PathVisualizer', 'ComparisonVisualizer', 'InteractiveVisualizer']
