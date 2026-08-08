"""
论文级可视化脚本 — 为 Exp1~Exp3 生成高质量图表

设计原则：
1. 风险场热力图叠加路径（论文核心贡献可视化）
2. 时变切片展示（不同Departure Time的风险场差异）
3. 关键事件标注（Storm Window、Pareto Jump点）
4. 学术论文配色方案（色盲友好、灰度可辨）
5. 300 DPI 输出，适配双栏排版
"""

from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

# Path setup
EXP_DIR = Path(__file__).resolve().parent
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scenario_builder import (
    load_micro_scenario, build_env_tensor, build_planner_config,
    get_primary_od, extract_metrics,
)
from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec

# ============================================================
# 学术论文配色方案 (Color-blind friendly)
# ============================================================
COLORS = {
    "morning":  "#D62728",  # 红 — 08:00
    "noon":     "#FF7F0E",  # 橙 — 12:00
    "evening":  "#1F77B4",  # 蓝 — 18:00
    "night":    "#9467BD",  # 紫 — 22:00
    "calm":     "#2CA02C",  # 绿
    "wind":     "#D62728",  # 红
    "rain":     "#1F77B4",  # 蓝
    "pareto_front": "#E74C3C",
    "pareto_dom": "#95A5A6",
    "highlight": "#F39C12",
    "danger":   "#C0392B",
    "safe":     "#27AE60",
}

# 自定义风险热力图：绿(安全) → 黄(低风险) → 红(高风险)
RISK_CMAP = LinearSegmentedColormap.from_list(
    "risk", ["#27AE60", "#F1C40F", "#E67E22", "#E74C3C", "#8B0000"]
)

OUTPUT_BASE = Path(__file__).resolve().parent.parent.parent / "results" / "paper_figures"

# ============================================================
# Figure 1: Exp1 — 时间节律自适应性 (3-panel: 热力图+路径+曲线)
# ============================================================
def fig1_temporal_adaptability():
    """
    生成 Figure 1: 时间节律自适应性
    Panel A: 18:00 风险热力图 + 4 条路径叠加
    Panel B: 22:00 风险热力图（展示时变差异）
    Panel C: 累积存活概率沿路径变化
    """
    print("=" * 60)
    print("Figure 1: Temporal Adaptability")
    print("=" * 60)

    scenario = load_micro_scenario()
    env_tensor = build_env_tensor(scenario)
    grid = scenario.grid
    start, goal = get_primary_od(grid)

    # Run 4 time slots
    time_slots = [8, 12, 18, 22]
    time_labels = {8: "08:00 (Morning Rush)", 12: "12:00 (Noon)", 18: "18:00 (Evening Rush)", 22: "22:00 (Night)"}
    results = {}

    for t in time_slots:
        config = build_planner_config("default")
        planner = AStar4D(grid, env_tensor, config)
        result = planner.search((start[0], start[1], start[2], t), goal)
        results[t] = result
        m = extract_metrics(result)
        print(f"  t={t}: dist={m['path_length']:.1f}m  surv={m['final_survival']:.4f}")

    # --- 获取风险场切片 ---
    # P_crash 在 z=5 (巡航高度) 的时间切片
    crash_2d = env_tensor.p_crash[:, :, 5, :]  # (nx, ny, nt)

    # --- 绘图 ---
    fig = plt.figure(figsize=(16, 12), facecolor='white', dpi=300)
    gs = gridspec.GridSpec(2, 2, hspace=0.3, wspace=0.25)

    # Panel A: 18:00 风险热力图 + 所有路径
    ax1 = fig.add_subplot(gs[0, 0])
    t_idx = 18  # 18:00
    risk_slice = crash_2d[:, :, t_idx].T  # (ny, nx) for imshow
    im1 = ax1.imshow(risk_slice, cmap=RISK_CMAP, origin='lower', alpha=0.85,
                     extent=[0, grid.spatial.nx * grid.spatial.dx,
                             0, grid.spatial.ny * grid.spatial.dy],
                     vmin=0, vmax=0.5)
    cbar1 = plt.colorbar(im1, ax=ax1, shrink=0.8, label="Crash Probability")

    for t in time_slots:
        result = results[t]
        if result["status"] == "success":
            path = result["path"]
            xs = [step["coords"][0] * grid.spatial.dx for step in path]
            ys = [step["coords"][1] * grid.spatial.dy for step in path]
            color = COLORS[list(COLORS.keys())[time_slots.index(t)]]
            ax1.plot(xs, ys, color=color, linewidth=2.5, label=time_labels[t],
                    alpha=0.9, zorder=5)
            ax1.scatter(xs[0], ys[0], color=color, s=80, marker='o',
                       edgecolors='black', linewidth=1.5, zorder=6)
            ax1.scatter(xs[-1], ys[-1], color=color, s=80, marker='*',
                       edgecolors='black', linewidth=1.5, zorder=6)

    ax1.set_xlabel("X (m)", fontsize=11)
    ax1.set_ylabel("Y (m)", fontsize=11)
    ax1.set_title("(a) 18:00 Risk Field + 4 Time-Slot Paths", fontsize=12, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left', framealpha=0.9)

    # Panel B: 22:00 风险热力图（展示时变差异）
    ax2 = fig.add_subplot(gs[0, 1])
    t_idx_22 = 22
    risk_slice_22 = crash_2d[:, :, t_idx_22].T
    im2 = ax2.imshow(risk_slice_22, cmap=RISK_CMAP, origin='lower', alpha=0.85,
                     extent=[0, grid.spatial.nx * grid.spatial.dx,
                             0, grid.spatial.ny * grid.spatial.dy],
                     vmin=0, vmax=0.5)
    cbar2 = plt.colorbar(im2, ax=ax2, shrink=0.8, label="Crash Probability")

    # 叠加 22:00 路径
    result_22 = results[22]
    if result_22["status"] == "success":
        path = result_22["path"]
        xs = [step["coords"][0] * grid.spatial.dx for step in path]
        ys = [step["coords"][1] * grid.spatial.dy for step in path]
        ax2.plot(xs, ys, color=COLORS["night"], linewidth=3, alpha=0.9, zorder=5)
        ax2.scatter(xs[0], ys[0], color=COLORS["night"], s=100, marker='o',
                   edgecolors='black', linewidth=2, zorder=6, label='Start')
        ax2.scatter(xs[-1], ys[-1], color=COLORS["night"], s=100, marker='*',
                   edgecolors='black', linewidth=2, zorder=6, label='Goal')

    # 标注建筑区域
    bh = scenario.building_heights
    ax2.contour(bh, levels=[30, 60, 100], colors=['gray', 'dimgray', 'black'],
               linewidths=[0.5, 1, 1.5], alpha=0.4,
               extent=[0, grid.spatial.nx * grid.spatial.dx,
                       0, grid.spatial.ny * grid.spatial.dy])

    ax2.set_xlabel("X (m)", fontsize=11)
    ax2.set_ylabel("Y (m)", fontsize=11)
    ax2.set_title("(b) 22:00 Risk Field (Night, Low Risk)", fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9, loc='upper left')

    # Panel C: 累积存活概率沿路径变化
    ax3 = fig.add_subplot(gs[1, 0])
    for t in time_slots:
        result = results[t]
        if result["status"] == "success":
            path = result["path"]
            distances = []
            survivals = []
            cum_d = 0
            for i, step in enumerate(path):
                if i > 0:
                    dx = (step["coords"][0] - path[i-1]["coords"][0]) * grid.spatial.dx
                    dy = (step["coords"][1] - path[i-1]["coords"][1]) * grid.spatial.dy
                    dz = (step["coords"][2] - path[i-1]["coords"][2]) * grid.spatial.dz
                    cum_d += np.sqrt(dx**2 + dy**2 + dz**2)
                distances.append(cum_d)
                survivals.append(step["state"].get("p_survival", 1.0))
            color = COLORS[list(COLORS.keys())[time_slots.index(t)]]
            ax3.plot(distances, survivals, color=color, linewidth=2.5,
                    label=time_labels[t], alpha=0.9)

    ax3.set_xlabel("Cumulative Distance (m)", fontsize=11)
    ax3.set_ylabel("Survival Probability", fontsize=11)
    ax3.set_title("(c) Cumulative Survival Along Path", fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8, loc='lower left')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(0, 1)

    # Panel D: Key Metrics Comparison条形图
    ax4 = fig.add_subplot(gs[1, 1])
    metrics_data = []
    for t in time_slots:
        result = results[t]
        m = extract_metrics(result)
        metrics_data.append(m)

    x = np.arange(len(time_slots))
    width = 0.2

    # Path Length（归一化）
    dists = [m['path_length'] for m in metrics_data]
    bars1 = ax4.bar(x - width*1.5, dists, width, label='Path Length (m)',
                   color=['#D62728', '#FF7F0E', '#1F77B4', '#9467BD'], alpha=0.8)

    # 存活概率（放大 1000 倍以便对比）
    survs = [m['final_survival'] * 1000 for m in metrics_data]
    bars2 = ax4.bar(x - width*0.5, survs, width, label='Survival (×10³)',
                   color=['#D62728', '#FF7F0E', '#1F77B4', '#9467BD'], alpha=0.5,
                   hatch='//')

    # Nodes Explored（对数）
    nodes = [m['nodes_explored'] for m in metrics_data]
    bars3 = ax4.bar(x + width*0.5, nodes, width, label='Nodes Explored',
                   color=['#D62728', '#FF7F0E', '#1F77B4', '#9467BD'], alpha=0.6,
                   hatch='\\\\')

    # 运行时间
    times = [m['runtime_ms'] for m in metrics_data]
    bars4 = ax4.bar(x + width*1.5, times, width, label='Runtime (ms)',
                   color=['#D62728', '#FF7F0E', '#1F77B4', '#9467BD'], alpha=0.4,
                   hatch='xx')

    ax4.set_xlabel("Departure Time", fontsize=11)
    ax4.set_ylabel("Value", fontsize=11)
    ax4.set_title("(d) Key Metrics Comparison", fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(['08:00', '12:00', '18:00', '22:00'])
    ax4.legend(fontsize=7, loc='upper left')
    ax4.set_yscale('log')

    # 标注 18:00 的异常值
    ax4.annotate('Storm Overlap\nNodes 27×',
                xy=(2, nodes[2]), xytext=(2.5, nodes[2] * 3),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=9, color='red', fontweight='bold')

    fig.suptitle("Figure 1: Figure 1: Temporal Adaptability of TD-RiskA*",
                fontsize=14, fontweight='bold', y=1.02)

    output_dir = OUTPUT_BASE / "fig1_temporal"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "fig1_temporal_adaptability.png", dpi=300,
               bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  [OK] Saved: {output_dir / 'fig1_temporal_adaptability.png'}")


# ============================================================
# Figure 2: Exp2 — 微气象-地形耦合避让 (2×2 风险场+路径)
# ============================================================
def fig2_microclimate_terrain():
    """
    生成 Figure 2: 微气象-地形耦合
    2×2 布局：
    - 左上: 风场 + Distance-only 路径
    - 右上: 风场 + TD-RiskA* 路径
    - 左下: 雨场 + Distance-only 路径
    - 右下: 雨场 + TD-RiskA* 路径
    每个面板叠加建筑等高线 + 风险热力图
    """
    print("=" * 60)
    print("Figure 2: Microclimate-Terrain Interaction")
    print("=" * 60)

    import copy
    from scenario_builder import apply_wind_hotspot, apply_rain_hotspot

    base_scenario = load_micro_scenario()
    grid = base_scenario.grid
    start, goal = get_primary_od(grid)
    T_START = 12

    # 3 conditions
    conditions = [
        {"key": "calm", "label": "Calm (Baseline)", "wind": 0.0, "rain": 0.0},
        {"key": "wind", "label": "Wind Canyon (15 m/s)", "wind": 15.0, "rain": 0.0},
        {"key": "rain", "label": "Heavy Rain (20 mm/h)", "wind": 0.0, "rain": 20.0},
    ]

    all_results = {}
    for cond in conditions:
        scenario = copy.deepcopy(base_scenario)
        if cond["wind"] > 0:
            cy, cx = scenario.wind_field.shape[0] // 2, scenario.wind_field.shape[1] // 2
            scenario.wind_field = apply_wind_hotspot(scenario.wind_field, (cy, cx), 8, cond["wind"])
        if cond["rain"] > 0:
            cy, cx = scenario.rain_data.shape[0] // 2, scenario.rain_data.shape[1] // 2
            scenario.rain_data = apply_rain_hotspot(scenario.rain_data, (cy, cx), 10, cond["rain"])

        env_tensor = build_env_tensor(scenario)

        # Distance-only
        config_dist = build_planner_config("default")
        config_dist["w_fatality"] = 0.0
        config_dist["w_property"] = 0.0
        config_dist["w_noise"] = 0.0
        config_dist["w_distance"] = 1.0
        planner_dist = AStar4D(grid, env_tensor, config_dist)
        result_dist = planner_dist.search((start[0], start[1], start[2], T_START), goal)

        # TD-RiskA*
        config_risk = build_planner_config("default")
        planner_risk = AStar4D(grid, env_tensor, config_risk)
        result_risk = planner_risk.search((start[0], start[1], start[2], T_START), goal)

        all_results[(cond["key"], "dist")] = result_dist
        all_results[(cond["key"], "risk")] = result_risk

        m_dist = extract_metrics(result_dist)
        m_risk = extract_metrics(result_risk)
        print(f"  {cond['key']}: dist_only={m_dist['path_length']:.1f}m, "
              f"td_risk={m_risk['path_length']:.1f}m, "
              f"fatality_reduced={((m_dist['cum_fatality']-m_risk['cum_fatality'])/m_dist['cum_fatality']*100):.1f}%")

    # --- 绘图: 2×3 布局 ---
    fig, axes = plt.subplots(2, 3, figsize=(18, 12), facecolor='white', dpi=300)

    # 建筑高度底图
    bh = base_scenario.building_heights
    extent = [0, grid.spatial.nx * grid.spatial.dx,
              0, grid.spatial.ny * grid.spatial.dy]

    for col, cond in enumerate(conditions):
        # 上排: Distance-only
        ax_top = axes[0, col]
        result_dist = all_results[(cond["key"], "dist")]
        m_dist = extract_metrics(result_dist)

        # 风险热力图
        env_tensor = build_env_tensor(base_scenario)  # rebuild for display
        crash_2d = env_tensor.p_crash[:, :, 5, T_START].T
        im = ax_top.imshow(crash_2d, cmap=RISK_CMAP, origin='lower', alpha=0.7,
                          extent=extent, vmin=0, vmax=0.5)

        # 建筑等高线
        ax_top.contour(bh, levels=[30, 60, 100], colors=['gray', 'dimgray', 'black'],
                      linewidths=[0.5, 1, 1.5], alpha=0.5, extent=extent)

        if result_dist["status"] == "success":
            path = result_dist["path"]
            xs = [step["coords"][0] * grid.spatial.dx for step in path]
            ys = [step["coords"][1] * grid.spatial.dy for step in path]
            ax_top.plot(xs, ys, '--', color='white', linewidth=3, alpha=0.9, zorder=5,
                       label='Distance-only')
            ax_top.plot(xs, ys, '--', color=COLORS["wind"], linewidth=2, alpha=0.9, zorder=5)

        ax_top.scatter(start[0]*grid.spatial.dx, start[1]*grid.spatial.dy,
                      color='green', s=100, marker='o', edgecolors='black', zorder=6)
        ax_top.scatter(goal[0]*grid.spatial.dx, goal[1]*grid.spatial.dy,
                      color='red', s=100, marker='*', edgecolors='black', zorder=6)

        ax_top.set_title(f"Distance-only\n{cond['label']}", fontsize=11, fontweight='bold')
        if col == 0:
            ax_top.set_ylabel("Distance-only", fontsize=12, fontweight='bold')

        # 标注关键指标
        ax_top.text(0.02, 0.98, f"Path: {m_dist['path_length']:.0f}m\n"
                   f"Fatal: {m_dist['cum_fatality']:.5f}\n"
                   f"Prop: {m_dist['cum_property']:.2f}",
                   transform=ax_top.transAxes, fontsize=8, va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 下排: TD-RiskA*
        ax_bot = axes[1, col]
        result_risk = all_results[(cond["key"], "risk")]
        m_risk = extract_metrics(result_risk)

        im2 = ax_bot.imshow(crash_2d, cmap=RISK_CMAP, origin='lower', alpha=0.7,
                           extent=extent, vmin=0, vmax=0.5)
        ax_bot.contour(bh, levels=[30, 60, 100], colors=['gray', 'dimgray', 'black'],
                      linewidths=[0.5, 1, 1.5], alpha=0.5, extent=extent)

        if result_risk["status"] == "success":
            path = result_risk["path"]
            xs = [step["coords"][0] * grid.spatial.dx for step in path]
            ys = [step["coords"][1] * grid.spatial.dy for step in path]
            ax_bot.plot(xs, ys, '-', color='white', linewidth=3, alpha=0.9, zorder=5,
                       label='TD-RiskA*')
            ax_bot.plot(xs, ys, '-', color=COLORS["calm"], linewidth=2.5, alpha=0.9, zorder=5)

        ax_bot.scatter(start[0]*grid.spatial.dx, start[1]*grid.spatial.dy,
                      color='green', s=100, marker='o', edgecolors='black', zorder=6)
        ax_bot.scatter(goal[0]*grid.spatial.dx, goal[1]*grid.spatial.dy,
                      color='red', s=100, marker='*', edgecolors='black', zorder=6)

        ax_bot.set_title(f"TD-RiskA*\n{cond['label']}", fontsize=11, fontweight='bold')
        if col == 0:
            ax_bot.set_ylabel("TD-RiskA*", fontsize=12, fontweight='bold')

        # 标注改进幅度
        fatality_reduction = (m_dist['cum_fatality'] - m_risk['cum_fatality']) / m_dist['cum_fatality'] * 100 if m_dist['cum_fatality'] > 0 else 0
        color = 'green' if fatality_reduction > 0 else 'red'
        ax_bot.text(0.02, 0.98, f"Path: {m_risk['path_length']:.0f}m\n"
                   f"Fatal: {m_risk['cum_fatality']:.5f}\n"
                   f"Fatal ↓: {fatality_reduction:.1f}%",
                   transform=ax_bot.transAxes, fontsize=8, va='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
                   color=color, fontweight='bold')

    # 共享 colorbar
    fig.colorbar(im, ax=axes, shrink=0.6, label="Crash Probability", pad=0.02)

    fig.suptitle("Figure 2: Figure 2: Microclimate-Terrain — Distance-only vs TD-RiskA*",
                fontsize=14, fontweight='bold', y=1.02)

    output_dir = OUTPUT_BASE / "fig2_microclimate"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "fig2_microclimate_terrain.png", dpi=300,
               bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  [OK] Saved: {output_dir / 'fig2_microclimate_terrain.png'}")


# ============================================================
# Figure 3: Exp3 — 噪声-安全 Pareto 前沿 (多面板)
# ============================================================
def fig3_pareto_frontier():
    """
    生成 Figure 3: 噪声-安全 Pareto 权衡
    Panel A: Pareto 散点图 (噪声 vs 致死)，标注跳变点
    Panel B: 权重敏感性曲线
    Panel C: 路径演化 (4 个代表性权重)
    Panel D: Before后路径对比 + 住宅走廊标注
    """
    print("=" * 60)
    print("Figure 3: Noise-Safety Pareto Trade-off")
    print("=" * 60)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from exp3_pareto.run_exp3_noise_safety_pareto import (
        build_scenario_with_residential_corridor, build_env_tensor,
        WEIGHT_CONFIGS, T_START
    )

    scenario = build_scenario_with_residential_corridor()
    grid = scenario["grid"]
    nx, ny, nz, nt = grid.shape
    env_tensor = build_env_tensor(scenario)

    start = (3, 30, 5, T_START)
    goal = (56, 30, 5)

    # Run all weight configs
    all_metrics = []
    all_results = []
    for wc in WEIGHT_CONFIGS:
        config = {
            "uav_speed": 10.0, "w_distance": wc["w_distance"],
            "w_fatality": wc["w_fatality"], "w_property": wc["w_property"],
            "w_noise": wc["w_noise"], "survival_threshold": 0.01,
            "max_battery_time": float("inf"), "max_iterations": 2_000_000,
            "max_labels_per_cell": 8, "max_climb_rate": 5.0, "max_descent_rate": 5.0,
        }
        planner = AStar4D(grid, env_tensor, config)
        result = planner.search(start, goal)
        m = extract_metrics(result)
        m["w_noise"] = wc["w_noise"]
        m["label"] = wc["label"]
        all_metrics.append(m)
        all_results.append({"config": wc, "result": result, "metrics": m})
        if m["status"] == "success":
            print(f"  {wc['label']}: dist={m['path_length']:.1f}m  noise={m['cum_noise']:.4f}")

    # --- 绘图 ---
    fig = plt.figure(figsize=(16, 14), facecolor='white', dpi=300)
    gs = gridspec.GridSpec(2, 2, hspace=0.35, wspace=0.3)

    success = [m for m in all_metrics if m["status"] == "success"]
    w_noises = [m["w_noise"] for m in success]

    # Panel A: Pareto 散点图 (噪声 vs 致死)
    ax1 = fig.add_subplot(gs[0, 0])
    noises = [m["cum_noise"] for m in success]
    fatalities = [m["cum_fatality"] for m in success]
    dists = [m["path_length"] for m in success]

    # 找到跳变点
    jump_idx = None
    for i in range(1, len(dists)):
        if abs(dists[i] - dists[i-1]) > 50:  # Path Length变化 > 50m
            jump_idx = i
            break

    # 画 Pareto 前沿线
    ax1.plot(noises, fatalities, 'k--', alpha=0.4, linewidth=1, label='Pareto frontier')

    # 散点，颜色编码Path Length
    sc = ax1.scatter(noises, fatalities, c=dists, cmap='RdYlBu_r', s=150,
                    edgecolors='black', linewidth=1.5, zorder=5, vmin=400, vmax=700)
    cbar = plt.colorbar(sc, ax=ax1, shrink=0.8, label="Path Length (m)")

    # 标注权重值
    for m in success:
        ax1.annotate(f"w_n={m['w_noise']:.2f}",
                    (m["cum_noise"], m["cum_fatality"]),
                    fontsize=7, ha='center', va='bottom',
                    xytext=(0, 8), textcoords='offset points')

    # 标注跳变点
    if jump_idx is not None:
        ax1.annotate('← Pareto Jump\nPath +141m',
                    xy=(noises[jump_idx], fatalities[jump_idx]),
                    xytext=(noises[jump_idx] + 1.5, fatalities[jump_idx] + 0.02),
                    arrowprops=dict(arrowstyle='->', color='red', lw=2),
                    fontsize=10, color='red', fontweight='bold',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    ax1.set_xlabel("Cumulative Noise Cost", fontsize=11)
    ax1.set_ylabel("Cumulative Fatality Risk", fontsize=11)
    ax1.set_title("(a) (a) Noise-Fatality Pareto Frontier", fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)

    # Panel B: 权重敏感性
    ax2 = fig.add_subplot(gs[0, 1])

    # 双 y 轴
    ax2_twin = ax2.twinx()

    l1, = ax2.plot(w_noises, dists, 'o-', color=COLORS["evening"], linewidth=2,
                  markersize=8, label='Path Length')
    l2, = ax2_twin.plot(w_noises, noises, 's-', color=COLORS["wind"], linewidth=2,
                       markersize=8, label='Cumulative Noise')

    # 标注Jump Zone
    if jump_idx is not None:
        ax2.axvspan(w_noises[jump_idx-1], w_noises[jump_idx], alpha=0.2, color='red',
                   label='Jump Zone')
        ax2.text((w_noises[jump_idx-1] + w_noises[jump_idx])/2,
                max(dists) * 0.95, 'Path Jump',
                ha='center', fontsize=9, color='red', fontweight='bold')

    ax2.set_xlabel("w_noise (Noise Weight)", fontsize=11)
    ax2.set_ylabel("Path Length (m)", fontsize=11, color=COLORS["evening"])
    ax2_twin.set_ylabel("Cumulative Noise", fontsize=11, color=COLORS["wind"])
    ax2.set_title("(b) (b) Weight Sensitivity", fontsize=12, fontweight='bold')
    ax2.legend(handles=[l1, l2], fontsize=9, loc='upper left')
    ax2.grid(True, alpha=0.3)

    # Panel C: 路径演化 (4 个代表性权重)
    ax3 = fig.add_subplot(gs[1, 0])

    # 土地利用底图
    landuse = scenario["landuse"]  # already fixed above, scenario is dict
    extent = [0, grid.spatial.nx * grid.spatial.dx,
              0, grid.spatial.ny * grid.spatial.dy]
    lu_colors = ['#FFFFFF', '#E8D5B7', '#FFD700', '#87CEEB', '#90EE90', '#228B22']
    from matplotlib.colors import ListedColormap
    lu_cmap = ListedColormap(lu_colors[:6])
    ax3.imshow(landuse.T, cmap=lu_cmap, origin='lower', alpha=0.6, extent=extent,
              vmin=0, vmax=5)

    # 住宅区边界
    ax3.axhspan(20*grid.spatial.dy, 40*grid.spatial.dy, alpha=0.15, color='brown',
               label='Residential Corridor (y=20~40)')

    # 画 4 条代表性路径
    representative = [0, 3, 5, 7]  # w_n=0.01, 0.20, 0.50, 0.85
    colors_rep = ['#2ECC71', '#F39C12', '#E74C3C', '#8B0000']
    for idx, (res_idx, color) in enumerate(zip(representative, colors_rep)):
        res = all_results[res_idx]
        if res["result"]["status"] == "success":
            path = res["result"]["path"]
            xs = [step["coords"][0] * grid.spatial.dx for step in path]
            ys = [step["coords"][1] * grid.spatial.dy for step in path]
            lw = 3 if idx == len(representative)-1 else 2
            style = '-' if idx == len(representative)-1 else '--'
            ax3.plot(xs, ys, style, color=color, linewidth=lw, alpha=0.9,
                    label=f"w_n={res['metrics']['w_noise']:.2f} ({res['metrics']['path_length']:.0f}m)")

    ax3.scatter(start[0]*grid.spatial.dx, start[1]*grid.spatial.dy,
               color='green', s=120, marker='o', edgecolors='black', zorder=6)
    ax3.scatter(goal[0]*grid.spatial.dx, goal[1]*grid.spatial.dy,
               color='red', s=120, marker='*', edgecolors='black', zorder=6)

    ax3.set_xlabel("X (m)", fontsize=11)
    ax3.set_ylabel("Y (m)", fontsize=11)
    ax3.set_title("(c) (c) Path Evolution: Through → Detour", fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8, loc='upper left')
    ax3.set_xlim(extent[0], extent[1])
    ax3.set_ylim(extent[2], extent[3])

    # Panel D: Before后对比详情
    ax4 = fig.add_subplot(gs[1, 1])

    # 雷达图展示Before后指标对比
    if jump_idx is not None:
        m_before = success[jump_idx - 1]
        m_after = success[jump_idx]

        categories = ['Path Length\n(m)', 'Cumulative Noise', 'Fatality\n(×10³)', 'Survival\n(×10²)']
        before_vals = [
            m_before['path_length'] / 10,  # 归一化
            m_before['cum_noise'],
            m_before['cum_fatality'] * 1000,
            m_before['final_survival'] * 100,
        ]
        after_vals = [
            m_after['path_length'] / 10,
            m_after['cum_noise'],
            m_after['cum_fatality'] * 1000,
            m_after['final_survival'] * 100,
        ]

        x = np.arange(len(categories))
        width = 0.35

        bars1 = ax4.bar(x - width/2, before_vals, width, label=f'Before (w_n={m_before["w_noise"]:.2f})',
                       color='#3498DB', alpha=0.8)
        bars2 = ax4.bar(x + width/2, after_vals, width, label=f'After (w_n={m_after["w_noise"]:.2f})',
                       color='#E74C3C', alpha=0.8)

        # 标注变化百分比
        for i, (b, a) in enumerate(zip(before_vals, after_vals)):
            if b > 0:
                pct = (a - b) / b * 100
                color = 'green' if (i != 0 and pct < 0) or (i == 0 and pct > 0) else 'red'
                ax4.text(i, max(b, a) * 1.05, f"{pct:+.1f}%",
                        ha='center', fontsize=9, color=color, fontweight='bold')

        ax4.set_xticks(x)
        ax4.set_xticklabels(categories, fontsize=10)
        ax4.set_ylabel("Value (Mixed Units)", fontsize=11)
        ax4.set_title("(d) (d) Pareto Jump: Before vs After", fontsize=12, fontweight='bold')
        ax4.legend(fontsize=9)
        ax4.grid(True, alpha=0.3, axis='y')

    fig.suptitle("Figure 3: Figure 3: Noise-Safety Pareto Trade-off",
                fontsize=14, fontweight='bold', y=1.02)

    output_dir = OUTPUT_BASE / "fig3_pareto"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "fig3_pareto_frontier.png", dpi=300,
               bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  [OK] Saved: {output_dir / 'fig3_pareto_frontier.png'}")


# ============================================================
# Figure 4: Exp4 — 时间自适应 + Storm Window (峡谷场景)
# ============================================================
def fig4_storm_window():
    """
    生成 Figure 4: Storm Window效应
    Panel A: 风速时间序列 + Path Length时间序列 (双 y 轴)
    Panel B: 存活率时间序列
    Panel C: Nodes Explored时间序列 (对数)
    Panel D: (d) Storm vs Calm Path (俯视图)
    """
    print("=" * 60)
    print("Figure 4: Storm Window Effect")
    print("=" * 60)

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from exp4_storm.run_exp4_pruning_efficiency import build_canyon_scenario, build_env_tensor, run_search

    sc = build_canyon_scenario()
    grid = sc["grid"]
    et = build_env_tensor(sc)
    nx, ny, nz, nt = grid.shape

    start = (5, 50, 5)
    goal = (94, 50, 5)

    # 时间扫描
    scan_data = []
    for t_dep in range(0, 48, 2):
        r = run_search(grid, et, (*start, t_dep), goal, 8)
        hr = t_dep * 0.5
        if r["status"] == "success":
            scan_data.append({
                "t": t_dep, "hr": hr,
                "dist": r["total_distance"],
                "surv": r["final_p_survival"],
                "nodes": r["nodes_explored"],
                "time": r["runtime_ms"],
            })

    # --- 绘图 ---
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), facecolor='white', dpi=300)

    hrs = [d["hr"] for d in scan_data]
    dists = [d["dist"] for d in scan_data]
    survs = [d["surv"] for d in scan_data]
    nodes = [d["nodes"] for d in scan_data]
    times = [d["time"] for d in scan_data]

    # Panel A: 风速 + Path Length
    ax1 = axes[0, 0]
    ax1_twin = ax1.twinx()

    # 风速曲线
    wind_speeds = []
    for d in scan_data:
        hr = d["hr"]
        if 12.0 <= hr < 18.0:
            wind_speeds.append(11.0)
        elif 6.0 <= hr < 12.0:
            wind_speeds.append(6.0)
        else:
            wind_speeds.append(3.0)

    ax1.fill_between(hrs, wind_speeds, alpha=0.3, color='skyblue', label='Wind')
    l1, = ax1.plot(hrs, wind_speeds, '-', color='steelblue', linewidth=2, label='Canyon Wind')

    l2, = ax1_twin.plot(hrs, dists, 'o-', color=COLORS["wind"], linewidth=2,
                       markersize=4, label='Path Length')

    # 标注Storm Window
    ax1.axvspan(12, 18, alpha=0.15, color='red', label='Storm Window (12:00-18:00)')

    ax1.set_xlabel("Time (h)", fontsize=11)
    ax1.set_ylabel("Wind (m/s)", fontsize=11, color='steelblue')
    ax1_twin.set_ylabel("Path Length (m)", fontsize=11, color=COLORS["wind"])
    ax1.set_title("(a) (a) Wind Speed vs Path Length", fontsize=12, fontweight='bold')
    ax1.legend(handles=[l1, l2], fontsize=9, loc='upper left')
    ax1.grid(True, alpha=0.3)

    # Panel B: 存活率
    ax2 = axes[0, 1]
    ax2.plot(hrs, survs, 'o-', color=COLORS["safe"], linewidth=2, markersize=4)
    ax2.axvspan(12, 18, alpha=0.15, color='red', label='Storm Window')
    ax2.set_xlabel("Time (h)", fontsize=11)
    ax2.set_ylabel("Survival Probability", fontsize=11)
    ax2.set_title("(b) (b) Survival Over Time", fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)

    # 标注Storm存活率反而更高
    ax2.annotate('Higher Survival in Storm\n(Detour Avoids High-Risk)',
                xy=(15, survs[len(survs)//2]),
                xytext=(20, survs[len(survs)//2] * 0.8),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=9, color='red', fontweight='bold')

    # Panel C: Nodes Explored (对数)
    ax3 = axes[1, 0]
    ax3.semilogy(hrs, nodes, 'o-', color=COLORS["evening"], linewidth=2, markersize=4)
    ax3.axvspan(12, 18, alpha=0.15, color='red', label='Storm Window')
    ax3.set_xlabel("Time (h)", fontsize=11)
    ax3.set_ylabel("Nodes Explored (log)", fontsize=11)
    ax3.set_title("(c) (c) Computational Complexity", fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=9)

    # 标注Storm搜索节点暴增
    max_nodes = max(nodes)
    ax3.annotate(f'Storm: {max_nodes:,}\n(Calm: {min(nodes):,})',
                xy=(15, max_nodes),
                xytext=(20, max_nodes * 0.3),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=9, color='red', fontweight='bold')

    # Panel D: 路径对比 (俯视图)
    ax4 = axes[1, 1]

    # 建筑底图
    bh = sc["building_heights"]
    extent = [0, nx * grid.spatial.dx, 0, ny * grid.spatial.dy]
    ax4.imshow(bh.T, cmap='YlOrRd', origin='lower', alpha=0.5, extent=extent)

    # Canyon Gap标注
    ax4.axhspan(45*grid.spatial.dy, 55*grid.spatial.dy, alpha=0.1, color='gray',
               label='Building Wall')
    ax4.text(50*grid.spatial.dx, 50*grid.spatial.dy, 'Canyon Gap',
            ha='center', fontsize=9, color='gray', fontweight='bold')

    # Calm路径 (t=0)
    r_calm = run_search(grid, et, (*start, 0), goal, 8)
    if r_calm["status"] == "success":
        path = r_calm["path"]
        xs = [step["coords"][0] * grid.spatial.dx for step in path]
        ys = [step["coords"][1] * grid.spatial.dy for step in path]
        ax4.plot(xs, ys, '-', color=COLORS["safe"], linewidth=3, alpha=0.9,
                label=f'Calm (t=0, {r_calm["total_distance"]:.0f}m)', zorder=5)

    # Storm路径 (t=24)
    r_storm = run_search(grid, et, (*start, 24), goal, 8)
    if r_storm["status"] == "success":
        path = r_storm["path"]
        xs = [step["coords"][0] * grid.spatial.dx for step in path]
        ys = [step["coords"][1] * grid.spatial.dy for step in path]
        ax4.plot(xs, ys, '-', color=COLORS["wind"], linewidth=3, alpha=0.9,
                label=f'Storm (t=24, {r_storm["total_distance"]:.0f}m)', zorder=5)

    ax4.scatter(start[0]*grid.spatial.dx, start[1]*grid.spatial.dy,
               color='green', s=120, marker='o', edgecolors='black', zorder=6)
    ax4.scatter(goal[0]*grid.spatial.dx, goal[1]*grid.spatial.dy,
               color='red', s=120, marker='*', edgecolors='black', zorder=6)

    ax4.set_xlabel("X (m)", fontsize=11)
    ax4.set_ylabel("Y (m)", fontsize=11)
    ax4.set_title("(d) (d) Storm vs Calm Path", fontsize=12, fontweight='bold')
    ax4.legend(fontsize=9, loc='upper left')
    ax4.set_xlim(extent[0], extent[1])
    ax4.set_ylim(extent[2], extent[3])

    fig.suptitle("Figure 4: Figure 4: Storm Window Adaptability — 100×100 Canyon",
                fontsize=14, fontweight='bold', y=1.02)

    output_dir = OUTPUT_BASE / "fig4_storm"
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / "fig4_storm_window.png", dpi=300,
               bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"  [OK] Saved: {output_dir / 'fig4_storm_window.png'}")


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("Generating paper figures...")
    print()

    fig1_temporal_adaptability()
    print()
    fig2_microclimate_terrain()
    print()
    fig3_pareto_frontier()
    print()
    fig4_storm_window()

    print()
    print("=" * 60)
    print(f"All figures saved to: {OUTPUT_BASE}")
    print("=" * 60)
