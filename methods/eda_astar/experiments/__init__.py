"""
Experiments Package for EDA-CostA* Algorithm Validation

This package contains independent experiment scripts for validating and comparing
the three path planning algorithms:

1. Experiment 01: Standard Cost A* - Baseline algorithm validation
2. Experiment 02: Original EDA-A* - EDA-optimized search region
3. Experiment 03: Two-Stage EDA-CostA* - Main contribution (EDA + advanced heuristics)
4. Experiment 04: Algorithm Comparison - Comprehensive performance comparison

Usage:
    # Run individual experiments
    uv run python experiments/experiment_01_standard_astar.py
    uv run python experiments/experiment_02_original_eda.py
    uv run python experiments/experiment_03_two_stage_eda.py
    
    # Run comparison
    uv run python experiments/experiment_04_comparison.py
"""
