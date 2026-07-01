"""
Experiment 3: Noise-Safety Pareto Trade-off

Core question: Does adjusting weights reveal a Pareto frontier between noise and safety?

Design:
- Fixed OD, fixed time (t=22, night)
- Scan w_noise from 0.05 to 0.50
- Algorithm: TD-RiskA*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from scenario_builder import load_micro_scenario, build_env_tensor, get_primary_od, extract_metrics

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T_START = 22

WEIGHT_CONFIGS = [
    {"label": "w_n=0.05", "w_distance": 0.65, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.05},
    {"label": "w_n=0.10", "w_distance": 0.60, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.10},
    {"label": "w_n=0.15", "w_distance": 0.55, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.15},
    {"label": "w_n=0.20", "w_distance": 0.50, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.20},
    {"label": "w_n=0.30", "w_distance": 0.40, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.30},
    {"label": "w_n=0.40", "w_distance": 0.30, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.40},
    {"label": "w_n=0.50", "w_distance": 0.20, "w_fatality": 0.25, "w_property": 0.05, "w_noise": 0.50},
]

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "EXP1-output" / "exp3_pareto"


def run_experiment():
    print("=" * 60)
    print("Experiment 3: Noise-Safety Pareto Trade-off")
    print("=" * 60)

    print("\n[1/4] Loading scenario...")
    scenario = load_micro_scenario()
    grid = scenario.grid
    start, goal = get_primary_od(grid)

    print("\n[2/4] Building risk tensor...")
    env_tensor = build_env_tensor(scenario)

    print("\n[3/4] Weight scan ({} configs)...".format(len(WEIGHT_CONFIGS)))
    all_results = []
    all_metrics = []

    for i, wc in enumerate(WEIGHT_CONFIGS):
        print("\n  [{}/{}] {}".format(i + 1, len(WEIGHT_CONFIGS), wc["label"]))

        config = {
            "uav_speed": 10.0,
            "w_distance": wc["w_distance"],
            "w_fatality": wc["w_fatality"],
            "w_property": wc["w_property"],
            "w_noise": wc["w_noise"],
            "survival_threshold": 0.01,
            "max_battery_time": float("inf"),
            "max_iterations": 500_000,
            "max_labels_per_cell": 8,
            "max_climb_rate": 5.0,
            "max_descent_rate": 5.0,
        }

        planner = AStar4D(grid, env_tensor, config)
        result = planner.search((start[0], start[1], start[2], T_START), goal)

        metrics = extract_metrics(result)
        metrics["w_noise"] = wc["w_noise"]
        metrics["w_distance"] = wc["w_distance"]
        metrics["label"] = wc["label"]
        all_metrics.append(metrics)
        all_results.append({"config": wc, "result": result, "metrics": metrics})

        if metrics["status"] == "success":
            print("    dist={:.1f}m noise={:.4f} fatality={:.8f} surv={:.6f}".format(
                metrics["path_length"], metrics["cum_noise"], metrics["cum_fatality"], metrics["final_survival"]))
        else:
            print("    Status: {}".format(metrics["status"]))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _save_metrics_csv(all_metrics)
    _plot_pareto_scatter(all_metrics)
    _plot_weight_sensitivity(all_metrics)
    _plot_metrics_table(all_metrics)

    print("\n[OK] Experiment 3 complete! Results: {}".format(OUTPUT_DIR))
    return all_results, all_metrics


def _save_metrics_csv(all_metrics):
    csv_path = OUTPUT_DIR / "metrics.csv"
    header = "label,w_noise,w_distance,status,path_length,final_survival,cum_fatality,cum_noise,objective_cost,runtime_ms,nodes_explored"
    lines = [header]
    for m in all_metrics:
        lines.append("{},{},{},{},{:.4f},{:.6f},{:.8f},{:.6f},{:.6f},{:.1f},{}".format(
            m["label"], m["w_noise"], m["w_distance"], m["status"],
            m["path_length"], m["final_survival"],
            m["cum_fatality"], m["cum_noise"], m["objective_cost"],
            m["runtime_ms"], m["nodes_explored"],
        ))
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] Saved: {}".format(csv_path))


def _plot_pareto_scatter(all_metrics):
    success = [m for m in all_metrics if m["status"] == "success"]
    if not success:
        print("  [WARN] No successful results, skipping Pareto plot")
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), facecolor="white")

    w_noises = [m["w_noise"] for m in success]
    distances = [m["path_length"] for m in success]
    noises = [m["cum_noise"] for m in success]
    fatalities = [m["cum_fatality"] for m in success]

    ax1 = axes[0]
    scatter1 = ax1.scatter(noises, distances, c=w_noises, cmap="viridis", s=100, edgecolors="black", zorder=5)
    ax1.plot(noises, distances, "k--", alpha=0.5, linewidth=1)
    ax1.set_xlabel("Cumulative Noise Cost", fontsize=12)
    ax1.set_ylabel("Path Length (m)", fontsize=12)
    ax1.set_title("Pareto: Noise vs Distance", fontsize=13, fontweight="bold")
    plt.colorbar(scatter1, ax=ax1, label="w_noise")
    ax1.grid(True, alpha=0.3)

    ax2 = axes[1]
    scatter2 = ax2.scatter(noises, fatalities, c=w_noises, cmap="viridis", s=100, edgecolors="black", zorder=5)
    ax2.plot(noises, fatalities, "k--", alpha=0.5, linewidth=1)
    ax2.set_xlabel("Cumulative Noise Cost", fontsize=12)
    ax2.set_ylabel("Cumulative Expected Fatality", fontsize=12)
    ax2.set_title("Pareto: Noise vs Fatality", fontsize=13, fontweight="bold")
    plt.colorbar(scatter2, ax=ax2, label="w_noise")
    ax2.grid(True, alpha=0.3)

    fig.suptitle("Exp3: Noise-Safety Pareto Trade-off", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_pareto_scatter.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_pareto_scatter.png")


def _plot_weight_sensitivity(all_metrics):
    success = [m for m in all_metrics if m["status"] == "success"]
    if not success:
        return

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), facecolor="white")
    w_noises = [m["w_noise"] for m in success]

    for key, title, ax in [
        ("path_length", "Path Length (m)", axes[0, 0]),
        ("cum_noise", "Cumulative Noise", axes[0, 1]),
        ("cum_fatality", "Cumulative Fatality", axes[1, 0]),
        ("final_survival", "Final Survival", axes[1, 1]),
    ]:
        values = [m[key] for m in success]
        ax.plot(w_noises, values, "o-", color="#3498DB", linewidth=2, markersize=8)
        ax.set_xlabel("w_noise", fontsize=11)
        ax.set_ylabel(title, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.3)

    fig.suptitle("Exp3: Weight Sensitivity", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_weight_sensitivity.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_weight_sensitivity.png")


def _plot_metrics_table(all_metrics):
    fig, ax = plt.subplots(figsize=(14, 6), facecolor="white")
    ax.axis("off")

    headers = ["Config", "w_noise", "Path(m)", "Survival", "Noise", "Fatality"]
    rows = []
    for m in all_metrics:
        rows.append([
            m["label"], "{:.2f}".format(m["w_noise"]),
            "{:.1f}".format(m["path_length"]) if m["status"] == "success" else "N/A",
            "{:.6f}".format(m["final_survival"]) if m["status"] == "success" else "N/A",
            "{:.4f}".format(m["cum_noise"]) if m["status"] == "success" else "N/A",
            "{:.8f}".format(m["cum_fatality"]) if m["status"] == "success" else "N/A",
        ])

    table = ax.table(cellText=rows, colLabels=headers, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.5)
    for j in range(len(headers)):
        table[0, j].set_facecolor("#8E44AD")
        table[0, j].set_text_props(color="white", fontweight="bold")
    for i in range(len(rows)):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[i + 1, j].set_facecolor("#F5EEF8")

    ax.set_title("Exp3: Pareto Trade-off - Metrics", fontsize=13, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_metrics_table.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_metrics_table.png")


if __name__ == "__main__":
    run_experiment()
