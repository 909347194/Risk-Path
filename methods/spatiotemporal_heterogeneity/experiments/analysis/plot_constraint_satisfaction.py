"""
缺口3 — 安全约束满足可视化（Constraint Satisfaction Visualization）

现有覆盖完全没有约束相关图。本脚本把 AStar4D 的硬约束逐条沿路径展开，
并给出"约束 × 出发时刻"的满足度矩阵，支撑核心主张：TD-RiskA* 的最优解
是在全部安全约束内取得的（可行域内最优，而非牺牲安全换性能）。

约束清单（与 src/algorithms/a_star/astar_4d.AStar4D 硬约束一一对应）：
  C1 存活概率       P_surv >= P_th          （survival_threshold）
  C2 建筑净空       clearance = z_c - h_bld > 0（obstacle 剪枝）
  C3 爬升率         climb  <= max_climb_rate
  C4 下降率         descent<= max_descent_rate
  C5 高度层         z_c ∈ [min_altitude, max_altitude]
  C6 续航时间       absolute_time <= max_battery_time

数据源：results/exp1_temporal/paths.json + 合成场景建筑高度（seed=42 复现）

产出（results/analysis_figures/constraint_satisfaction/）：
- figB_constraint_satisfaction.png   2×2：存活/净空/垂直速率/满足度矩阵
- constraint_margins.csv             逐步约束裕度明细（数据留档）

用法：
    python plot_constraint_satisfaction.py [--paths PATHS_JSON] [--out OUT_DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    CONSTRAINTS,
    EXP1_PATHS,
    MICRO_GRID,
    OUTPUT_BASE,
    coords_array,
    display_label,
    label_sort_key,
    load_path_records,
    save_fig,
    setup_style,
    state_series,
    TIME_COLORS,
)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402


def _load_building_heights() -> Optional[np.ndarray]:
    """复现场景的建筑高度场 (ny, nx, 米)；失败返回 None。"""
    common_dir = Path(__file__).resolve().parent.parent / "common"
    if str(common_dir) not in sys.path:
        sys.path.insert(0, str(common_dir))
    try:
        from scenario_builder import load_micro_scenario
        scenario = load_micro_scenario()
        return np.asarray(scenario.building_heights, dtype=float)
    except Exception as exc:  # 场景依赖缺失时优雅降级
        print(f"  [WARN] 建筑高度加载失败（{exc}），净空面板将跳过")
        return None


def compute_margins(record: Dict[str, Any],
                    building_heights: Optional[np.ndarray]) -> Dict[str, np.ndarray]:
    """沿路径计算每个约束的裕度（margin > 0 表示满足）。"""
    coords = coords_array(record)                     # (N, 4) x,y,z,t
    series = state_series(record)
    dx = MICRO_GRID["dx"]
    dy = MICRO_GRID["dy"]
    dz = MICRO_GRID["dz"]

    # C1 存活概率裕度
    survival_margin = series["p_survival"] - CONSTRAINTS["survival_threshold"]

    # 层中心高度 z_c = (z + 1) * dz（与 astar_4d._get_neighbors 一致）
    altitude = (coords[:, 2] + 1.0) * dz

    # C2 建筑净空裕度
    if building_heights is not None:
        bh = building_heights[coords[:, 1], coords[:, 0]]
        clearance = altitude - bh
    else:
        bh = np.full(len(coords), np.nan)
        clearance = np.full(len(coords), np.nan)

    # 分段物理距离与垂直速率
    seg_dist = np.zeros(len(coords))
    vert_rate = np.zeros(len(coords))
    for i in range(1, len(coords)):
        ddx = (coords[i, 0] - coords[i - 1, 0]) * dx
        ddy = (coords[i, 1] - coords[i - 1, 1]) * dy
        ddz = (coords[i, 2] - coords[i - 1, 2]) * dz
        seg_dist[i] = float(np.sqrt(ddx**2 + ddy**2 + ddz**2))
        dt_seg = seg_dist[i] / CONSTRAINTS["uav_speed"]
        if dt_seg > 0:
            vert_rate[i] = abs(ddz) / dt_seg
    climb_rate = np.where(coords[:, 2] > np.roll(coords[:, 2], 1), vert_rate, 0.0)
    descent_rate = np.where(coords[:, 2] < np.roll(coords[:, 2], 1), vert_rate, 0.0)
    climb_rate[0] = 0.0
    descent_rate[0] = 0.0

    # C5 高度层裕度
    alt_margin = np.minimum(altitude - CONSTRAINTS["min_altitude"],
                            CONSTRAINTS["max_altitude"] - altitude)

    # C6 续航时间裕度
    battery_margin = CONSTRAINTS["max_battery_time"] - series["absolute_time"]

    return {
        "cum_distance": series["cum_distance"],
        "p_survival": series["p_survival"],
        "survival_margin": survival_margin,
        "altitude": altitude,
        "building_height": bh,
        "clearance": clearance,
        "climb_rate": climb_rate,
        "descent_rate": descent_rate,
        "alt_margin": alt_margin,
        "battery_margin": battery_margin,
    }


def _time_color(key: str) -> str:
    return TIME_COLORS.get(int(key), "#555555") if str(key).isdigit() else "#555555"


# ============================================================
# 面板
# ============================================================
def panel_survival(ax, all_margins: Dict[str, Dict[str, np.ndarray]]) -> None:
    """(a) 存活概率约束：曲线 + 阈值线 + 违禁区。"""
    p_th = CONSTRAINTS["survival_threshold"]
    for key in sorted(all_margins, key=label_sort_key):
        m = all_margins[key]
        ax.plot(m["cum_distance"], m["p_survival"], color=_time_color(key),
                linewidth=2, label=display_label(key))
    ax.axhline(p_th, color="red", linewidth=1.6, linestyle="--",
               label=f"Survival threshold P_th = {p_th}")
    ax.axhspan(0, p_th, color="red", alpha=0.12)
    ax.text(0.99, p_th * 1.6, "violation zone", color="red", fontsize=8,
            ha="right", va="bottom")
    ax.set_xlabel("Cumulative distance (m)")
    ax.set_ylabel("Survival probability $P_{surv}$")
    ax.set_title("(a) C1: Survival probability constraint")
    ax.set_ylim(0, 1.02)
    ax.legend(loc="lower left", fontsize=8)


def panel_clearance(ax, ax_twin, key: str, m: Dict[str, np.ndarray]) -> None:
    """(b) 高度剖面与建筑净空（代表出发时刻）。"""
    dist = m["cum_distance"]
    alt = m["altitude"]
    bh = m["building_height"]

    if np.all(np.isnan(bh)):
        ax.text(0.5, 0.5, "building heights unavailable", ha="center",
                va="center", transform=ax.transAxes)
        return

    ax.fill_between(dist, 0, bh, step="mid", color="#95A5A6", alpha=0.65,
                    label="Building height under path")
    ax.step(dist, bh, where="mid", color="#7F8C8D", linewidth=1.0)
    ax.plot(dist, alt, color="#2980B9", linewidth=2.2, linestyle="-",
            label="Flight altitude (layer center)")

    # 净空为正填绿、为负填红
    if np.any(alt > bh):
        ax.fill_between(dist, bh, alt, step="mid", where=(alt > bh),
                        color="#27AE60", alpha=0.25, label="Clearance > 0")
    if np.any(alt <= bh):
        ax.fill_between(dist, bh, alt, step="mid", where=(alt <= bh),
                        color="#C0392B", alpha=0.4, label="Clearance ≤ 0")

    min_clear = float(np.nanmin(m["clearance"]))
    min_idx = int(np.nanargmin(m["clearance"]))
    ax.annotate(
        f"min clearance = {min_clear:.1f} m @ {dist[min_idx]:.0f} m",
        xy=(dist[min_idx], alt[min_idx]),
        xytext=(10, 24), textcoords="offset points", fontsize=8,
        arrowprops=dict(arrowstyle="->", color="#2C3E50", lw=1.2),
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    if min_clear > 0 and float(np.nanmax(bh)) == 0.0:
        ax.text(
            0.02, 0.02,
            "Path overflies no buildings — horizontal avoidance keeps "
            "clearance = cruise altitude",
            transform=ax.transAxes, fontsize=8, color="#2C3E50",
            bbox=dict(boxstyle="round", facecolor="#ECF0F1", alpha=0.9),
        )
    ax.set_xlabel("Cumulative distance (m)")
    ax.set_ylabel("Height (m)")
    ax.set_title(f"(b) C2: Building clearance profile — {display_label(key)}")
    ax.legend(loc="upper right", fontsize=8)

    ax_twin.plot(dist, m["clearance"], color="#27AE60", linewidth=1.4,
                 linestyle=":", label="Clearance margin")
    ax_twin.set_ylabel("Clearance margin (m)", color="#27AE60")
    ax_twin.tick_params(axis="y", labelcolor="#27AE60")


def panel_vertical(ax, key: str, m: Dict[str, np.ndarray]) -> None:
    """(c) 爬升/下降率约束（代表出发时刻）。"""
    dist = m["cum_distance"]
    ax.step(dist, m["climb_rate"], where="mid", color="#E67E22", linewidth=1.8,
            label="Climb rate")
    ax.step(dist, -m["descent_rate"], where="mid", color="#8E44AD", linewidth=1.8,
            label="Descent rate")

    max_c = CONSTRAINTS["max_climb_rate"]
    max_d = CONSTRAINTS["max_descent_rate"]
    ax.axhline(max_c, color="#E67E22", linestyle="--", linewidth=1.4,
               label=f"max climb = {max_c:.1f} m/s")
    ax.axhline(-max_d, color="#8E44AD", linestyle="--", linewidth=1.4,
               label=f"max descent = {max_d:.1f} m/s")
    ax.axhspan(max_c, max_c * 1.6, color="red", alpha=0.10)
    ax.axhspan(-max_d * 1.6, -max_d, color="red", alpha=0.10)

    if float(np.max(m["climb_rate"])) == 0.0 and float(np.max(m["descent_rate"])) == 0.0:
        ax.text(0.5, 0.08, "No vertical maneuver on path — constraint inactive by plan",
                transform=ax.transAxes, ha="center", fontsize=9, color="#2C3E50",
                bbox=dict(boxstyle="round", facecolor="#ECF0F1", alpha=0.9))

    ax.set_xlabel("Cumulative distance (m)")
    ax.set_ylabel("Vertical rate (m/s)")
    ax.set_title(f"(c) C3/C4: Climb & descent rate limits — {display_label(key)}")
    ax.set_ylim(-max_d * 1.7, max_c * 1.7)
    ax.legend(loc="upper right", fontsize=8)


def panel_matrix(ax, all_margins: Dict[str, Dict[str, np.ndarray]]) -> None:
    """(d) 约束满足度矩阵：约束 × 出发时刻。"""
    keys = sorted(all_margins, key=label_sort_key)

    # (显示名, 裕度字段, 裕度计算函数, 警戒阈值的尺度函数)
    def _min_margin(m, field):
        return float(np.nanmin(m[field]))

    def _climb_margin(m):
        return float(CONSTRAINTS["max_climb_rate"] - np.max(m["climb_rate"]))

    def _descent_margin(m):
        return float(CONSTRAINTS["max_descent_rate"] - np.max(m["descent_rate"]))

    constraints = [
        ("C1 Survival ≥ P_th", "survival_margin",
         lambda m: _min_margin(m, "survival_margin"),
         lambda m: max(abs(m["survival_margin"]).max(), 1e-3)),
        ("C2 Clearance > 0", "clearance",
         lambda m: _min_margin(m, "clearance"),
         lambda m: max(np.nanmax(np.abs(m["clearance"])), 1.0)),
        ("C3 Climb ≤ max", "climb_rate", _climb_margin,
         lambda m: CONSTRAINTS["max_climb_rate"]),
        ("C4 Descent ≤ max", "descent_rate", _descent_margin,
         lambda m: CONSTRAINTS["max_descent_rate"]),
        ("C5 Altitude band", "alt_margin",
         lambda m: _min_margin(m, "alt_margin"),
         lambda m: max(MICRO_GRID["dz"], 1.0)),
        ("C6 Battery time", "battery_margin",
         lambda m: _min_margin(m, "battery_margin"),
         lambda m: 1.0),
    ]

    n_rows = len(constraints)
    n_cols = len(keys)
    status_img = np.zeros((n_rows, n_cols))
    texts: List[List[str]] = [[""] * n_cols for _ in range(n_rows)]

    for ci, key in enumerate(keys):
        m = all_margins[key]
        for ri, (cname, field, margin_fn, scale_fn) in enumerate(constraints):
            values = m[field]
            if np.all(np.isinf(values)):
                status_img[ri, ci] = 3.0  # inactive（约束未启用，如电池预算 = inf）
                texts[ri][ci] = "inactive"
                continue
            margin = margin_fn(m)
            scale = float(scale_fn(m))
            ratio = margin / scale if scale > 0 else margin
            if margin <= 0:
                status_img[ri, ci] = 0.0   # violated
                mark = "✗"
            elif ratio < 0.2:
                status_img[ri, ci] = 1.0   # near limit
                mark = "△"
            else:
                status_img[ri, ci] = 2.0   # satisfied
                mark = "✓"
            texts[ri][ci] = f"{mark} {margin:.3g}"

    cmap = ListedColormap(["#C0392B", "#F1C40F", "#27AE60", "#BDC3C7"])
    ax.imshow(status_img, cmap=cmap, vmin=-0.5, vmax=3.5, aspect="auto")

    for ri in range(n_rows):
        for ci in range(n_cols):
            ax.text(ci, ri, texts[ri][ci], ha="center", va="center",
                    fontsize=8, color="white", fontweight="bold")

    ax.set_xticks(range(n_cols))
    ax.set_xticklabels([display_label(k) for k in keys], fontsize=8, rotation=15)
    ax.set_yticks(range(n_rows))
    ax.set_yticklabels([c[0] for c in constraints], fontsize=9)
    ax.grid(False)
    ax.set_title("(d) Constraint satisfaction matrix (min margin)")
    ax.set_xlabel("")
    # 图例
    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#27AE60"),
        plt.Rectangle((0, 0), 1, 1, color="#F1C40F"),
        plt.Rectangle((0, 0), 1, 1, color="#C0392B"),
        plt.Rectangle((0, 0), 1, 1, color="#BDC3C7"),
    ]
    ax.legend(handles, ["✓ satisfied", "△ near limit", "✗ violated", "inactive"],
              loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8)


def export_margins_csv(all_margins: Dict[str, Dict[str, np.ndarray]],
                       out_dir: Path) -> None:
    """逐步约束裕度明细留档。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "constraint_margins.csv"
    header = ("label,step,cum_distance,p_survival,survival_margin,"
              "altitude_m,building_height_m,clearance_m,"
              "climb_rate,descent_rate,alt_margin,battery_margin")
    lines = [header]
    for key in sorted(all_margins, key=label_sort_key):
        m = all_margins[key]
        n = len(m["cum_distance"])
        for i in range(n):
            lines.append(",".join([
                str(key), str(i),
                f"{m['cum_distance'][i]:.4f}",
                f"{m['p_survival'][i]:.6f}",
                f"{m['survival_margin'][i]:.6f}",
                f"{m['altitude'][i]:.2f}",
                f"{m['building_height'][i]:.2f}",
                f"{m['clearance'][i]:.2f}",
                f"{m['climb_rate'][i]:.4f}",
                f"{m['descent_rate'][i]:.4f}",
                f"{m['alt_margin'][i]:.2f}",
                f"{m['battery_margin'][i]:.1f}",
            ]))
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Saved: {target}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="缺口3 安全约束满足可视化")
    parser.add_argument("--paths", type=Path, default=EXP1_PATHS,
                        help="含逐步 states 的 paths.json（exp1 格式）")
    parser.add_argument("--out", type=Path,
                        default=OUTPUT_BASE / "constraint_satisfaction",
                        help="输出目录")
    args = parser.parse_args(argv)

    setup_style()
    print("=" * 60)
    print("Safety Constraint Satisfaction (gap #3)")
    print("=" * 60)
    print(f"  Data: {args.paths}")

    records = load_path_records(args.paths)
    records = {k: r for k, r in records.items() if r["states"]}
    if not records:
        raise SystemExit("没有可用的逐步 states 数据，无法生成约束图")

    building_heights = _load_building_heights()
    all_margins = {k: compute_margins(r, building_heights) for k, r in records.items()}
    # 代表时次取数值出发时刻的中间时段（信息量大），否则取第一个
    numeric_keys = sorted([k for k in all_margins if str(k).isdigit()], key=label_sort_key)
    rep_key = numeric_keys[len(numeric_keys) // 2] if numeric_keys else sorted(all_margins)[0]
    print(f"  Records: {sorted(records.keys(), key=label_sort_key)}")
    print(f"  Representative record: {rep_key}")

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    panel_survival(axes[0][0], all_margins)
    panel_clearance(axes[0][1], axes[0][1].twinx(), rep_key, all_margins[rep_key])
    panel_vertical(axes[1][0], rep_key, all_margins[rep_key])
    panel_matrix(axes[1][1], all_margins)

    fig.suptitle("Safety Constraint Satisfaction Along Planned Paths (TD-RiskA*)",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    save_fig(fig, args.out, "figB_constraint_satisfaction.png")
    export_margins_csv(all_margins, args.out)


if __name__ == "__main__":
    main()
