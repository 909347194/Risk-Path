# Experiments - Algorithm Validation and Comparison

This directory contains independent experiment scripts for validating the three path planning algorithms implemented in this project.

---

## 📋 Available Experiments

### Experiment 01: Standard Cost A* ⭐
**File**: `experiment_01_standard_astar.py`

**Purpose**: Validate the baseline Cost A* algorithm with integrated risk assessment.

**What it tests**:
- ✅ 26-neighborhood movement in 3D space
- ✅ Collision avoidance with buildings
- ✅ Integrated cost model (fatality + property + noise + traffic)
- ✅ Optimal path finding

**Run**:
```bash
uv run python experiments/experiment_01_standard_astar.py
```

**Output**: `output/experiment_01/`
- `results.json` - Path coordinates and metrics
- `path_3d.png` - 3D visualization of the path

---

### Experiment 02: Original EDA-A* ⭐
**File**: `experiment_02_original_eda.py`

**Purpose**: Validate the Original EDA-A* algorithm that uses EDA to optimize the search region.

**What it tests**:
- ✅ EDA probability matrix initialization and update
- ✅ Elite population selection
- ✅ Search region optimization
- ✅ Nested EDA + A* structure

**Run**:
```bash
uv run python experiments/experiment_02_original_eda.py
```

**Output**: `output/experiment_02/`
- `results.json` - Path and EDA metrics
- `path_3d.png` - 3D path visualization
- `eda_convergence.png` - EDA convergence curve

---

### Experiment 03: Two-Stage EDA-CostA* ⭐⭐⭐
**File**: `experiment_03_two_stage_eda.py`

**Purpose**: Validate the main contribution - Two-Stage EDA-CostA* with advanced heuristics.

**What it tests**:
- ✅ Stage 1: EDA optimization for search space reduction
- ✅ Stage 2: K-means clustering and advanced heuristic computation
- ✅ Stage 3: Enhanced CostA* with adaptive heuristic switching
- ✅ Formula 24-26 implementation

**Run**:
```bash
uv run python experiments/experiment_03_two_stage_eda.py
```

**Output**: `output/experiment_03/`
- `results.json` - Comprehensive results with stage-by-stage metrics
- `path_3d.png` - 3D path visualization
- `eda_convergence.png` - EDA convergence
- `clustering_results.png` - K-means clustering visualization
- `cost_map_slices.png` - Cost map at different altitudes

---

### Experiment 04: Algorithm Comparison ⭐⭐
**File**: `experiment_04_comparison.py`

**Purpose**: Compare all three algorithms on the same scenario to evaluate relative performance.

**What it compares**:
- Total cost (risk + distance)
- Number of waypoints
- Computation time
- Solution quality

**Run**:
```bash
uv run python experiments/experiment_04_comparison.py
```

**Output**: `output/experiment_04_comparison/`
- `comparison_results.json` - Side-by-side comparison data
- `path_comparison.png` - All three paths overlaid
- `performance_comparison.png` - Bar charts of metrics

---

## 🎯 Expected Results

Based on validation tests, you should see:

| Algorithm | Cost | Waypoints | Time |
|-----------|------|-----------|------|
| Standard Cost A* | ~98.17 | ~73 | ~2s |
| Original EDA-A* | ~99.00 | ~75 | ~15s |
| Two-Stage EDA-CostA* | ~98.17 | ~73 | ~20s |

**Key Insight**: Two-Stage EDA achieves the same optimal cost as Standard A* while demonstrating the effectiveness of EDA-based search space optimization.

---

## 📊 Output Structure

```
output/
├── experiment_01/              # Standard A* results
│   ├── results.json
│   └── *.png (visualizations)
│
├── experiment_02/              # Original EDA results
│   ├── results.json
│   └── *.png (visualizations)
│
├── experiment_03/              # Two-Stage EDA results
│   ├── results.json
│   └── *.png (visualizations)
│
└── experiment_04_comparison/   # Comparison results
    ├── comparison_results.json
    └── *.png (comparative visualizations)
```

---

## 🔧 Customization

To modify experiment parameters:

1. **Grid settings**: Edit bounds and cell_size in each script
2. **EDA parameters**: Modify `eda_params` dictionary
3. **Start/Goal points**: Change `start` and `goal` tuples
4. **Visualization**: Enable/disable by commenting out viz calls

---

## 📝 Notes

- Each experiment is **independent** - can be run separately
- Results are saved to `output/` directory automatically
- Visualizations use matplotlib/seaborn (300 DPI for publication quality)
- For real-world testing, replace placeholder data loading with actual GIS data

---

**Last Updated**: 2026-04-27
