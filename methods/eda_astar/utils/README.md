# Utils - Utility Modules

This directory contains reusable utility modules for the EDA-CostA* project.

---

## 📦 Available Utilities

### 1. Visualization Tools (`visualizer.py`)

Reusable visualization classes for experiments and analysis.

#### PathVisualizer
For single algorithm experiment visualizations:
- `plot_path_3d()` - 3D path visualization
- `plot_cost_map_slices()` - Cost map horizontal slices
- `plot_eda_convergence()` - EDA convergence curves
- `plot_clustering_results()` - K-means clustering visualization

#### ComparisonVisualizer
For algorithm comparison visualizations:
- `plot_path_comparison()` - Overlay multiple paths
- `plot_performance_comparison()` - Bar charts of metrics

**Usage Example**:
```python
from utils.visualizer import PathVisualizer

viz = PathVisualizer(output_dir="output/experiment_01")
viz.plot_path_3d(path, cost_map)
viz.plot_eda_convergence(convergence_history)
```

---

## 🔧 Adding New Utilities

When adding new utility modules:

1. Create the module file (e.g., `data_loader.py`)
2. Export it in `__init__.py`
3. Add documentation here
4. Include usage examples

---

**Last Updated**: 2026-04-27
