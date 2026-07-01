"""
Experiment 4: Pruning Efficiency

Core question: Is Label-Setting pruning faster without losing optimality?

Design:
- Fixed OD, fixed time (t=12), fixed weight (default)
- Compare 5 pruning strategies with different max_labels_per_cell
- Ablation: scan max_labels from 1 to 50
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from scenario_builder import (
    load_micro_scenario, build_env_tensor, build_planner_config,
    get_primary_od, extract_metrics,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T_START = 12

PRUNING_STRATEGIES = [
    {"name": "No Pruning (k=50)", "max_labels": 50, "color": "#E74C3C"},
    {"name": "Strict (k=1)", "max_labels": 1, "color": "#F39C12"},
    {"name": "Proposed (k=4)", "max_labels": 4, "color": "#2ECC71"},
    {"name": "Proposed (k=8)", "max_labels": 8, "color": "#3498DB"},
    {"name": "Proposed (k=16)", "max_labels": 16, "color": "#9B59B6"},
]

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "EXP1-output" / "exp4_pruning"


def run_experiment():
    print("=" * 60)
    print("Experiment 4: Pruning Efficiency")
    print("=" * 60)

    print("\n[1/4] Loading scenario...")
    scenario = load_micro_scenario()
    grid = scenario.grid
    start, goal = get_primary_od(grid)

    print("\n[2/4] Building risk tensor...")
    env_tensor = build_env_tensor(scenario)

    print("\n[3/4] Pruning strategy comparison ({} strategies)...".format(len(PRUNING_STRATEGIES)))
    all_results = []
    all_metrics = []

    for strategy in PRUNING_STRATEGIES:
        print("\n  --- {} ---".format(strategy["name"]))

        config = build_planner_config("default", max_labels_per_cell=strategy["max_labels"])
        planner = AStar4D(grid, env_tensor, config)
        result = planner.search((start[0], start[1], start[2], T_START), goal)

        metrics = extract_metrics(result)
        metrics["strategy"] = strategy["name"]
        metrics["max_labels"] = strategy["max_labels"]
        all_metrics.append(metrics)
        all_results.append({"strategy": strategy, "result": result, "metrics": metrics})

        print("    Status: {}".format(metrics["status"]))
        if metrics["status"] == "success":
            print("    Path: {:.1f}m, Cost: {:.6f}, Time: {:.1f}ms, Nodes: {}".format(
                metrics["path_length"], metrics["objective_cost"], metrics["runtime_ms"], metrics["nodes_explored"]))

    print("\n[3.5/4] Ablation: max_labels scan...")
    ablation_results = _run_ablation(grid, env_tensor, start, goal)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _save_metrics_csv(all_metrics)
    _save_ablation_csv(ablation_results)

    print("\n[4/4] Generating figures...")
    _plot_runtime_comparison(all_metrics)
    _plot_ablation_curve(ablation_results)
    _plot_cost_vs_speed(all_metrics)

    print("\n[OK] Experiment 4 complete! Results: {}".format(OUTPUT_DIR))
    return all_results, all_metrics


def _run_ablation(grid, env_tensor, start, goal):
    label_values = [1, 2, 4, 6, 8, 12, 16, 24, 32, 50]
    results = []
    for k in label_values:
        config = build_planner_config("default", max_labels_per_cell=k)
        planner = AStar4D(grid, env_tensor, config)
        result = planner.search((start[0], start[1], start[2], T_START), goal)
        metrics = extract_metrics(result)
        metrics["max_labels"] = k
        results.append(metrics)
        status_str = "cost={:.6f}".format(metrics["objective_cost"]) if metrics["status"] == "success" else metrics["status"]
        print("    k={:2d}: time={:.1f}ms nodes={} {}".format(k, metrics["runtime_ms"], metrics["nodes_explored"], status_str))
    return results


def _save_metrics_csv(all_metrics):
    csv_path = OUTPUT_DIR / "metrics.csv"
    header = "strategy,max_labels,status,path_length,objective_cost,runtime_ms,nodes_explored"
    lines = [header]
    for m in all_metrics:
        lines.append("{},{},{},{:.4f},{:.6f},{:.1f},{}".format(
            m["strategy"], m["max_labels"], m["status"],
            m["path_length"], m["objective_cost"], m["runtime_ms"], m["nodes_explored"],
        ))
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] Saved: {}".format(csv_path))


def _save_ablation_csv(ablation_results):
    csv_path = OUTPUT_DIR / "ablation_labels.csv"
    header = "max_labels,status,objective_cost,runtime_ms,nodes_explored"
    lines = [header]
    for m in ablation_results:
        lines.append("{},{},{:.6f},{:.1f},{}".format(
            m["max_labels"], m["status"], m["objective_cost"], m["runtime_ms"], m["nodes_explored"],
        ))
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] Saved: {}".format(csv_path))


def _plot_runtime_comparison(all_metrics):
    success = [m for m in all_metrics if m["status"] == "success"]
    if not success:
        print("  [WARN] No successful results")
        return

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor="white")
    names = [m["strategy"] for m in success]
    colors = [s["color"] for s in PRUNING_STRATEGIES if any(m["strategy"] == s["name"] and m["status"] == "success" for m in all_metrics)]

    ax1 = axes[0]
    runtimes = [m["runtime_ms"] for m in success]
    ax1.bar(range(len(names)), runtimes, color=colors, edgecolor="black", alpha=0.8)
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax1.set_ylabel("Runtime (ms)", fontsize=11)
    ax1.set_title("Runtime Comparison", fontsize=12, fontweight="bold")

    ax2 = axes[1]
    nodes = [m["nodes_explored"] for m in success]
    ax2.bar(range(len(names)), nodes, color=colors, edgecolor="black", alpha=0.8)
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax2.set_ylabel("Nodes Explored", fontsize=11)
    ax2.set_title("Search Scale", fontsize=12, fontweight="bold")

    ax3 = axes[2]
    costs = [m["objective_cost"] for m in success]
    ax3.bar(range(len(names)), costs, color=colors, edgecolor="black", alpha=0.8)
    ax3.set_xticks(range(len(names)))
    ax3.set_xticklabels(names, rotation=30, ha="right", fontsize=9)
    ax3.set_ylabel("Objective Cost", fontsize=11)
    ax3.set_title("Optimality", fontsize=12, fontweight="bold")

    fig.suptitle("Exp4: Pruning Strategy Comparison", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_runtime_comparison.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_runtime_comparison.png")


def _plot_ablation_curve(ablation_results):
    success = [m for m in ablation_results if m["status"] == "success"]
    if not success:
        return

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), facecolor="white")
    k_values = [m["max_labels"] for m in success]

    ax1 = axes[0]
    ax1.plot(k_values, [m["runtime_ms"] for m in success], "o-", color="#3498DB", linewidth=2, markersize=8)
    ax1.set_xlabel("max_labels_per_cell", fontsize=11)
    ax1.set_ylabel("Runtime (ms)", fontsize=11)
    ax1.set_title("Runtime vs Label Cap", fontsize=12, fontweight="bold")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    ax2.plot(k_values, [m["objective_cost"] for m in success], "s-", color="#E74C3C", linewidth=2, markersize=8)
    ax2.set_xlabel("max_labels_per_cell", fontsize=11)
    ax2.set_ylabel("Objective Cost", fontsize=11)
    ax2.set_title("Optimality vs Label Cap", fontsize=12, fontweight="bold")
    ax2.grid(True, alpha=0.3)

    ax3 = axes[2]
    ax3.plot(k_values, [m["nodes_explored"] for m in success], "^-", color="#2ECC71", linewidth=2, markersize=8)
    ax3.set_xlabel("max_labels_per_cell", fontsize=11)
    ax3.set_ylabel("Nodes Explored", fontsize=11)
    ax3.set_title("Search Scale vs Label Cap", fontsize=12, fontweight="bold")
    ax3.grid(True, alpha=0.3)

    fig.suptitle("Exp4: max_labels_per_cell Ablation", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_ablation_curve.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_ablation_curve.png")


def _plot_cost_vs_speed(all_metrics):
    success = [m for m in all_metrics if m["status"] == "success"]
    if not success:
        return

    fig, ax = plt.subplots(figsize=(8, 6), facecolor="white")

    for m in success:
        strategy = next(s for s in PRUNING_STRATEGIES if s["name"] == m["strategy"])
        ax.scatter(m["runtime_ms"], m["objective_cost"], s=150, color=strategy["color"], edgecolors="black", zorder=5, label=m["strategy"])

    ax.set_xlabel("Runtime (ms)", fontsize=12)
    ax.set_ylabel("Objective Cost", fontsize=12)
    ax.set_title("Optimality vs Speed Trade-off", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_cost_vs_speed.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_cost_vs_speed.png")


if __name__ == "__main__":
    run_experiment()
