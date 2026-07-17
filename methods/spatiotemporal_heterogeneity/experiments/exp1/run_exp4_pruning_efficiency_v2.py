"""
Experiment 4 IMPROVED: Label-Setting Pruning Efficiency

=== 改进设计 ===

问题根因：40×40 网格 + 24 时间步 → 仅 179 搜索节点，标签冲突为零，
         k=1 和 k=50 结果完全相同，无法体现 Label-Setting 优势。

改进策略：
1. 宏观网格 100×100×12×96 — 搜索空间扩大 100 倍
2. 15 分钟时间步（96 步）— 更细时间粒度产生更多标签冲突
3. 复杂风/雨/人口动态 — 同一空间位置在不同时刻有不同风险 → 标签非支配
4. 多 OD 对测试 — 消除单 OD 偶然性
5. 消融实验扫描 k=1→200 — 完整的计算-最优性权衡曲线

预期结论：
- 小 k：搜索快但可能次优（过度剪枝丢弃了 Pareto 最优标签）
- 大 k：最优但慢（保留太多标签）
- 最优 k*：在最优性和计算效率之间的平衡点
- Label-Setting (k=4~8) 优于 Node-Setting (k=1) 和 No Pruning (k=∞)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_p_crash import DynamicCrashProbability
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_fatality import DynamicFatalityModel
from methods.spatiotemporal_heterogeneity.src.tensor_engine.static_obstacle import PropertyDamageModel
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_noise import DynamicNoiseCost
from methods.spatiotemporal_heterogeneity.src.algorithms.env_tensor import EnvTensor
from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D
from methods.spatiotemporal_heterogeneity.utils.synthetic_data_factory import generate_synthetic_city

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output" / "EXP1-output" / "exp4_pruning_v2"


# ===== 宏观场景构建 =====

def build_macro_scenario(seed=42):
    """
    构建宏观场景：100×100×12×96（50m分辨率，15min/步）。

    关键改进：
    - 网格面积扩大 6.25× (5000m vs 800m)
    - 时间步从 1h 细化到 15min（96 步 vs 24 步）
    - 复杂风/雨/人口动态 → 同一位置不同时刻风险不同 → 标签冲突
    """
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=100, ny=100, nz=12, dx=50.0, dy=50.0, dz=10.0),
        temporal=TemporalGridConfig(nt=96, dt_minutes=15.0),
    )
    nx, ny, nz, nt = grid.shape
    print(f"  Grid: {nx}×{ny}×{nz}×{nt} = {nx*ny*nz*nt:,} cells")

    city_data = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=seed)
    landuse = city_data["landuse"].astype(np.int32)

    # 注入复杂时空动态
    wind_field = city_data["wind_field"].astype(np.float32)
    rain_data = city_data["rain_data"].astype(np.float32)

    # 风场：多个时空热点
    cy, cx = ny // 2, nx // 2
    yy, xx = np.mgrid[0:ny, 0:nx]

    # 热点1：中心，12-18 时强风
    dist1 = (xx - cx) ** 2 + (yy - cy) ** 2
    hotspot1 = np.exp(-dist1 / (2 * 12 ** 2))
    # 热点2：左上角，6-10 时中风
    dist2 = (xx - 20) ** 2 + (yy - 80) ** 2
    hotspot2 = np.exp(-dist2 / (2 * 8 ** 2))
    # 热点3：右下角，18-22 时中风
    dist3 = (xx - 80) ** 2 + (yy - 20) ** 2
    hotspot3 = np.exp(-dist3 / (2 * 8 ** 2))

    for t in range(nt):
        hour = t * 0.25  # 15min steps
        if 12 <= hour <= 18:
            wind_factor1 = 6.0
        elif 6 <= hour <= 11:
            wind_factor1 = 2.0
        else:
            wind_factor1 = 0.5

        if 6 <= hour <= 10:
            wind_factor2 = 5.0
        else:
            wind_factor2 = 0.5

        if 18 <= hour <= 22:
            wind_factor3 = 5.0
        else:
            wind_factor3 = 0.5

        for iz in range(nz):
            wind_field[:, :, iz, t] += hotspot1 * wind_factor1
            wind_field[:, :, iz, t] += hotspot2 * wind_factor2
            wind_field[:, :, iz, t] += hotspot3 * wind_factor3

    # 降雨：下午时段
    rain_hotspot = np.exp(-dist1 / (2 * 15 ** 2))
    for t in range(nt):
        hour = t * 0.25
        if 14 <= hour <= 20:
            rain_data[:, :, t] += rain_hotspot * 12.0

    return {
        "grid": grid,
        "landuse": landuse,
        "building_heights": city_data["building_heights"].astype(np.float32),
        "population": city_data["population"].astype(np.float32),
        "wind_field": wind_field,
        "rain_data": rain_data,
    }


def build_env_tensor_macro(scenario, flight_altitude=50.0):
    """构建宏观环境张量。"""
    grid = scenario["grid"]
    nx, ny, nz, nt = grid.shape
    landuse = scenario["landuse"]

    # 1. P_crash
    crash_model = DynamicCrashProbability()
    wind_2d = np.transpose(scenario["wind_field"][:, :, 0, :], (1, 0, 2))
    rain_2d = np.transpose(scenario["rain_data"], (1, 0, 2))

    f_wind = crash_model.compute_wind_factor(wind_2d[:, :, np.newaxis, :])
    f_rain = crash_model.compute_rain_factor(rain_2d[:, :, np.newaxis, :])
    f_obs = np.ones((nx, ny, nz, nt), dtype=np.float32)
    p_crash = crash_model.compute_pcrash(f_wind, f_rain, f_obs, dt=grid.temporal.dt_minutes * 60.0)
    p_crash = np.clip(p_crash, 0.0, 1.0).astype(np.float32)

    # 2. 潮汐人口
    landuse_t = np.transpose(landuse, (1, 0))
    base_pop = np.transpose(scenario["population"], (1, 0))
    rho_pop_3d = np.zeros((nx, ny, nt), dtype=np.float32)

    for t in range(nt):
        hour = t * 0.25
        pop_t = base_pop.copy()
        if 8 <= hour <= 18:
            pop_t[landuse_t == 2] *= 5.0
        else:
            pop_t[landuse_t == 2] *= 0.1
        if 22 <= hour or hour <= 6:
            pop_t[landuse_t == 1] *= 4.0
        elif 9 <= hour <= 17:
            pop_t[landuse_t == 1] *= 0.2
        if 8 <= hour <= 17:
            pop_t[landuse_t == 3] *= 4.0
        else:
            pop_t[landuse_t == 3] *= 0.2
        rho_pop_3d[:, :, t] = pop_t

    rho_vehicle_3d = rho_pop_3d * 0.1

    # 3. E_fatality
    fatality_model = DynamicFatalityModel()
    e_fatality_3d = fatality_model.compute_fatality_consequence(
        rho_pop=rho_pop_3d, rho_vehicle=rho_vehicle_3d, flight_altitude=flight_altitude,
    )
    e_fatality = np.broadcast_to(e_fatality_3d[:, :, np.newaxis, :], (nx, ny, nz, nt)).astype(np.float32)

    # 4. E_property
    building_t = np.transpose(scenario["building_heights"], (1, 0))
    prop_model = PropertyDamageModel(
        building_heights=building_t, max_prop_damage=1000.0,
        log_normal_mu=3.04, log_normal_sigma=0.5,
    )
    e_property = prop_model.compute_property_consequence(flight_altitude=flight_altitude).astype(np.float32)

    # 5. R_noise
    noise_model = DynamicNoiseCost(grid=grid)
    r_noise = noise_model.compute_noise_cost(
        landuse=landuse_t, population_density=rho_pop_3d,
    ).astype(np.float32)

    # 6. 障碍物
    obstacle = np.zeros((nx, ny, nz), dtype=np.float32)
    for iz in range(nz):
        z_height = (iz + 1.0) * grid.spatial.dz
        obstacle[:, :, iz] = (building_t >= z_height).astype(np.float32)

    return EnvTensor(
        p_crash=p_crash, fatality=e_fatality, property=e_property,
        noise=r_noise, obstacle=obstacle, grid=grid,
    )


# ===== 多 OD 对定义 =====

@dataclass
class ODPair:
    name: str
    start: Tuple[int, int, int, int]  # (x, y, z, t)
    goal: Tuple[int, int, int]         # (x, y, z)
    description: str


def get_od_pairs(grid) -> List[ODPair]:
    """定义多组 OD 对，覆盖不同路径场景。"""
    nx, ny = grid.spatial.nx, grid.spatial.ny
    return [
        ODPair(
            name="diagonal",
            start=(5, 5, 5, 12),
            goal=(nx - 6, ny - 6, 5),
            description="SW→NE diagonal, long range"
        ),
        ODPair(
            name="cross_center",
            start=(5, ny // 2, 5, 12),
            goal=(nx - 6, ny // 2, 5),
            description="W→E through center, medium range"
        ),
        ODPair(
            name="short_hop",
            start=(20, 20, 5, 12),
            goal=(80, 80, 5),
            description="Medium diagonal, avoids edges"
        ),
    ]


# ===== 单次搜索运行 =====

@dataclass
class SearchResult:
    od_name: str
    max_labels: int
    status: str
    path_length: float
    objective_cost: float
    runtime_ms: float
    nodes_explored: int
    labels_created: int


def run_single_search(grid, env_tensor, od: ODPair, max_labels: int) -> SearchResult:
    """执行一次 A* 搜索。"""
    config = {
        "uav_speed": 15.0,
        "w_distance": 0.40,
        "w_fatality": 0.30,
        "w_property": 0.15,
        "w_noise": 0.15,
        "survival_threshold": 0.01,
        "max_battery_time": float("inf"),
        "max_iterations": 5_000_000,
        "max_labels_per_cell": max_labels,
        "max_climb_rate": 5.0,
        "max_descent_rate": 5.0,
    }

    planner = AStar4D(grid, env_tensor, config)
    result = planner.search(od.start, od.goal)

    return SearchResult(
        od_name=od.name,
        max_labels=max_labels,
        status=result["status"],
        path_length=result.get("total_distance", float("inf")),
        objective_cost=result.get("objective_cost", float("inf")),
        runtime_ms=result.get("time_cost", 0) * 1000,
        nodes_explored=result.get("nodes_explored", 0),
        labels_created=result.get("nodes_explored", 0),  # 近似
    )


# ===== 主实验 =====

def run_experiment():
    print("=" * 60)
    print("Experiment 4 IMPROVED: Label-Setting Pruning Efficiency")
    print("=" * 60)

    print("\n[1/4] Building macro scenario (100×100×12×96)...")
    scenario = build_macro_scenario()
    grid = scenario["grid"]

    print("\n[2/4] Building risk tensor...")
    env_tensor = build_env_tensor_macro(scenario)
    print(f"  EnvTensor: {env_tensor.shape}")

    ods = get_od_pairs(grid)
    print(f"\n[3/4] Running experiments ({len(ods)} OD pairs × multiple k values)...")

    # ===== 消融实验：k 从 1 到 100 =====
    k_values = [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, 32, 48, 64, 100]
    all_results: List[SearchResult] = []

    for od in ods:
        print(f"\n  === OD: {od.name} ({od.description}) ===")
        for k in k_values:
            result = run_single_search(grid, env_tensor, od, k)
            all_results.append(result)
            status_str = f"cost={result.objective_cost:.4f}" if result.status == "success" else result.status
            print(f"    k={k:3d}: time={result.runtime_ms:7.1f}ms  nodes={result.nodes_explored:6d}  {status_str}")

    # ===== 核心策略对比 =====
    print(f"\n[3.5/4] Strategy comparison...")
    strategies = [
        {"name": "Node-Setting (k=1)", "k": 1, "color": "#E74C3C"},
        {"name": "Label-Setting (k=4)", "k": 4, "color": "#2ECC71"},
        {"name": "Label-Setting (k=8)", "k": 8, "color": "#3498DB"},
        {"name": "Label-Setting (k=16)", "k": 16, "color": "#9B59B6"},
        {"name": "No Pruning (k=100)", "k": 100, "color": "#F39C12"},
    ]

    strategy_results = []
    for od in ods:
        for s in strategies:
            result = run_single_search(grid, env_tensor, od, s["k"])
            result_dict = {
                "od": od.name, "strategy": s["name"], "k": s["k"],
                "status": result.status,
                "path_length": result.path_length,
                "objective_cost": result.objective_cost,
                "runtime_ms": result.runtime_ms,
                "nodes_explored": result.nodes_explored,
            }
            strategy_results.append(result_dict)
            print(f"    {od.name} | {s['name']}: {result.status}  "
                  f"dist={result.path_length:.1f}m  J={result.objective_cost:.4f}  "
                  f"time={result.runtime_ms:.1f}ms")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _save_ablation_csv(all_results)
    _save_strategy_csv(strategy_results)
    _plot_ablation_curves(all_results, k_values, ods)
    _plot_strategy_comparison(strategy_results, strategies, ods)
    _plot_cost_vs_speed(all_results, ods)
    _plot_runtime_heatmap(all_results, k_values, ods)

    print(f"\n[OK] Experiment 4 v2 complete! Results: {OUTPUT_DIR}")
    return all_results, strategy_results


# ===== 保存结果 =====

def _save_ablation_csv(results: List[SearchResult]):
    csv_path = OUTPUT_DIR / "ablation_labels.csv"
    lines = ["od,max_labels,status,path_length,objective_cost,runtime_ms,nodes_explored"]
    for r in results:
        lines.append(f"{r.od_name},{r.max_labels},{r.status},{r.path_length:.4f},"
                     f"{r.objective_cost:.6f},{r.runtime_ms:.1f},{r.nodes_explored}")
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Saved: {csv_path}")


def _save_strategy_csv(results: List[dict]):
    csv_path = OUTPUT_DIR / "strategy_comparison.csv"
    lines = ["od,strategy,max_labels,status,path_length,objective_cost,runtime_ms,nodes_explored"]
    for r in results:
        lines.append(f"{r['od']},{r['strategy']},{r['k']},{r['status']},"
                     f"{r['path_length']:.4f},{r['objective_cost']:.6f},"
                     f"{r['runtime_ms']:.1f},{r['nodes_explored']}")
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Saved: {csv_path}")


# ===== 可视化 =====

def _plot_ablation_curves(results: List[SearchResult], k_values: List[int], ods: List[ODPair]):
    """消融曲线：k vs 运行时间/最优性/搜索节点（每个 OD 一条线）。"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6), facecolor="white")
    colors = ["#E74C3C", "#3498DB", "#2ECC71"]

    for od_idx, od in enumerate(ods):
        od_results = [r for r in results if r.od_name == od.name and r.status == "success"]
        if not od_results:
            continue
        ks = [r.max_labels for r in od_results]
        runtimes = [r.runtime_ms for r in od_results]
        costs = [r.objective_cost for r in od_results]
        nodes = [r.nodes_explored for r in od_results]
        c = colors[od_idx % len(colors)]

        axes[0].plot(ks, runtimes, "o-", color=c, linewidth=2, markersize=6, label=od.name)
        axes[1].plot(ks, costs, "s-", color=c, linewidth=2, markersize=6, label=od.name)
        axes[2].plot(ks, nodes, "^-", color=c, linewidth=2, markersize=6, label=od.name)

    for ax, ylabel, title in [
        (axes[0], "Runtime (ms)", "Runtime vs max_labels"),
        (axes[1], "Objective Cost (J)", "Optimality vs max_labels"),
        (axes[2], "Nodes Explored", "Search Scale vs max_labels"),
    ]:
        ax.set_xlabel("max_labels_per_cell", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.set_xscale("log")

    fig.suptitle("Exp4 v2: Label-Setting Ablation (Macro 100×100×96)",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_ablation_curve.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] Saved: fig_ablation_curve.png")


def _plot_strategy_comparison(results: List[dict], strategies: List[dict], ods: List[ODPair]):
    """策略对比柱状图：每个 OD 一组柱子。"""
    fig, axes = plt.subplots(1, 3, figsize=(20, 6), facecolor="white")
    metrics = [
        ("runtime_ms", "Runtime (ms)", axes[0]),
        ("objective_cost", "Objective Cost", axes[1]),
        ("nodes_explored", "Nodes Explored", axes[2]),
    ]

    x = np.arange(len(ods))
    width = 0.15

    for s_idx, s in enumerate(strategies):
        for metric_key, ylabel, ax in metrics:
            values = []
            for od in ods:
                r = next((r for r in results if r["od"] == od.name and r["strategy"] == s["name"]), None)
                values.append(r[metric_key] if r else 0)
            ax.bar(x + s_idx * width, values, width, label=s["name"],
                   color=s["color"], edgecolor="black", alpha=0.8)

    for ax, ylabel, title in metrics:
        ax.set_xlabel("OD Pair", fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xticks(x + width * 2)
        ax.set_xticklabels([od.name for od in ods], fontsize=9)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.3, axis="y")

    fig.suptitle("Exp4 v2: Strategy Comparison (Macro Grid)",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_strategy_comparison.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] Saved: fig_strategy_comparison.png")


def _plot_cost_vs_speed(results: List[SearchResult], ods: List[ODPair]):
    """计算-最优性权衡散点图：运行时间 vs 目标函数。"""
    fig, ax = plt.subplots(figsize=(10, 7), facecolor="white")
    colors = {"diagonal": "#E74C3C", "cross_center": "#3498DB", "short_hop": "#2ECC71"}

    for od in ods:
        od_results = [r for r in results if r.od_name == od.name and r.status == "success"]
        runtimes = [r.runtime_ms for r in od_results]
        costs = [r.objective_cost for r in od_results]
        ks = [r.max_labels for r in od_results]

        c = colors.get(od.name, "gray")
        ax.scatter(runtimes, costs, c=c, s=60, edgecolors="black", zorder=5, label=od.name)
        ax.plot(runtimes, costs, "--", color=c, alpha=0.4, linewidth=1)

        # 标注 k 值
        for r, k in zip(od_results, ks):
            if k in [1, 4, 8, 16, 100]:
                ax.annotate(f"k={k}", (r.runtime_ms, r.objective_cost),
                            fontsize=7, ha="center", va="bottom", color=c)

    ax.set_xlabel("Runtime (ms)", fontsize=12)
    ax.set_ylabel("Objective Cost (J)", fontsize=12)
    ax.set_title("Exp4 v2: Optimality vs Speed Trade-off", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_cost_vs_speed.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] Saved: fig_cost_vs_speed.png")


def _plot_runtime_heatmap(results: List[SearchResult], k_values: List[int], ods: List[ODPair]):
    """热力图：OD × k → 运行时间。"""
    fig, ax = plt.subplots(figsize=(14, 5), facecolor="white")

    data = np.zeros((len(ods), len(k_values)))
    for i, od in enumerate(ods):
        for j, k in enumerate(k_values):
            r = next((r for r in results if r.od_name == od.name and r.max_labels == k), None)
            data[i, j] = r.runtime_ms if r and r.status == "success" else 0

    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", origin="lower")
    ax.set_xticks(range(len(k_values)))
    ax.set_xticklabels(k_values, fontsize=9)
    ax.set_yticks(range(len(ods)))
    ax.set_yticklabels([od.name for od in ods], fontsize=10)
    ax.set_xlabel("max_labels_per_cell", fontsize=11)
    ax.set_ylabel("OD Pair", fontsize=11)
    ax.set_title("Exp4 v2: Runtime Heatmap (ms)", fontsize=13, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Runtime (ms)")

    # 标注数值
    for i in range(len(ods)):
        for j in range(len(k_values)):
            if data[i, j] > 0:
                ax.text(j, i, f"{data[i, j]:.0f}", ha="center", va="center", fontsize=7)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_runtime_heatmap.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("  [OK] Saved: fig_runtime_heatmap.png")


if __name__ == "__main__":
    run_experiment()
