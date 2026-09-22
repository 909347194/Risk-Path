"""
缺口1 — 沿路径累积风险分量逐步分解图（Risk Decomposition Along Path）

现有覆盖只有"总量曲线"（fig_cumulative_curves.png），本脚本补充分量级的
逐步分解，支撑核心主张：累积风险由致死/财产/噪声三分量共同构成，
且不同出发时刻的分量构成与累积节奏显著不同（时空异质性）。

数据源：results/exp1_temporal/paths.json（含逐步 states 的 exp1 格式）

产出（results/analysis_figures/risk_decomposition/）：
- figA1_risk_decomposition.png          代表出发时刻：堆积分解 + 逐步增量
- figA2_risk_decomposition_timeslots.png 全部出发时刻的小多图堆积分解

用法：
    python plot_risk_decomposition.py [--paths PATHS_JSON] [--out OUT_DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    COMPONENT_COLORS,
    COMPONENT_KEYS,
    COMPONENT_LABELS,
    EXP1_PATHS,
    OUTPUT_BASE,
    coords_array,
    display_label,
    label_sort_key,
    load_path_records,
    save_fig,
    setup_style,
    state_series,
    TIME_COLORS,
    TIME_LABELS,
)

import matplotlib.pyplot as plt  # noqa: E402


def _time_color(key: str) -> str:
    return TIME_COLORS.get(int(key), "#555555") if str(key).isdigit() else "#555555"


def _record_series(record: Dict[str, Any]) -> Dict[str, np.ndarray]:
    return state_series(record)


def _increments(series: Dict[str, np.ndarray], key: str) -> np.ndarray:
    """逐步增量 ΔC_i（首步为 0）。"""
    values = series[key]
    return np.diff(values, prepend=values[0])


def fig_a1(records: Dict[str, Dict[str, Any]], out_dir: Path) -> None:
    """代表出发时刻：(a) 堆积分解 (b) 逐步增量。"""
    # 代表时次 = 累积总风险最大的出发时刻（信息量最大）
    totals = {}
    for key, record in records.items():
        series = _record_series(record)
        totals[key] = float(sum(series[k][-1] for k in COMPONENT_KEYS))
    rep_key = max(totals, key=totals.get)

    series = _record_series(records[rep_key])
    dist = series["cum_distance"]
    label = display_label(rep_key)

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

    # ---------- (a) 堆积面积分解 ----------
    ax = axes[0]
    comp_values = [series[k] for k in COMPONENT_KEYS]
    total = np.sum(comp_values, axis=0)
    ax.stackplot(
        dist, *comp_values,
        labels=[COMPONENT_LABELS[k] for k in COMPONENT_KEYS],
        colors=[COMPONENT_COLORS[k] for k in COMPONENT_KEYS],
        alpha=0.85,
    )
    ax.plot(dist, total, color="black", linewidth=1.8, linestyle="--",
            label="Total accumulated risk")
    final_txt = " + ".join(
        f"{COMPONENT_LABELS[k].split()[0]} {series[k][-1]:.2e}" for k in COMPONENT_KEYS
    )
    ax.text(
        0.98, 0.70,
        f"Final: {final_txt}\nTotal = {total[-1]:.2e}",
        transform=ax.transAxes, ha="right", va="top", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    ax.set_xlabel("Cumulative distance (m)")
    ax.set_ylabel("Cumulative risk contribution")
    ax.set_title(f"(a) Cumulative risk decomposition — {label}")
    ax.legend(loc="upper left", fontsize=8)
    ax.set_xlim(dist[0], dist[-1])

    # ---------- (b) 逐步增量分解 ----------
    ax = axes[1]
    for key in COMPONENT_KEYS:
        delta = _increments(series, key)
        ax.step(dist, delta, where="mid", color=COMPONENT_COLORS[key],
                linewidth=1.8, label=f"Δ {COMPONENT_LABELS[key]}")
        ax.fill_between(dist, 0, delta, step="mid",
                        color=COMPONENT_COLORS[key], alpha=0.15)
    ax.set_xlabel("Cumulative distance (m)")
    ax.set_ylabel("Per-step risk increment ΔC")
    ax.set_title("(b) Stepwise risk increments along path")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(dist[0], dist[-1])

    fig.suptitle("Risk Decomposition Along Path (TD-RiskA*)",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_fig(fig, out_dir, "figA1_risk_decomposition.png")


def fig_a2(records: Dict[str, Dict[str, Any]], out_dir: Path) -> None:
    """全部出发时刻的小多图：堆积分解的时变差异。"""
    keys = sorted(records.keys(), key=label_sort_key)

    # 统一 y 轴上限，便于跨时次比较
    y_max = 0.0
    for key in keys:
        series = _record_series(records[key])
        total = sum(float(series[k][-1]) for k in COMPONENT_KEYS)
        y_max = max(y_max, total)
    y_max *= 1.15

    n = len(keys)
    ncols = 2
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 4.2 * nrows),
                             squeeze=False)

    for idx, key in enumerate(keys):
        ax = axes[idx // ncols][idx % ncols]
        series = _record_series(records[key])
        dist = series["cum_distance"]
        comp_values = [series[k] for k in COMPONENT_KEYS]
        total = np.sum(comp_values, axis=0)

        ax.stackplot(
            dist, *comp_values,
            labels=[COMPONENT_LABELS[k] for k in COMPONENT_KEYS],
            colors=[COMPONENT_COLORS[k] for k in COMPONENT_KEYS],
            alpha=0.85,
        )
        ax.plot(dist, total, color="black", linewidth=1.4, linestyle="--")

        shares = {k: (float(series[k][-1]) / total[-1] * 100.0 if total[-1] > 0 else 0.0)
                  for k in COMPONENT_KEYS}
        dominant = max(shares, key=shares.get)
        ax.set_title(
            f"{display_label(key)}  —  total {total[-1]:.2e}, "
            f"dominant: {COMPONENT_LABELS[dominant].split()[0]} ({shares[dominant]:.0f}%)",
            fontsize=10,
        )
        ax.set_xlabel("Cumulative distance (m)")
        ax.set_ylabel("Cumulative risk contribution")
        ax.set_xlim(dist[0], dist[-1])
        ax.set_ylim(0, y_max)
        if idx == 0:
            ax.legend(loc="upper left", fontsize=8)

    # 隐藏多余子图
    for idx in range(n, nrows * ncols):
        axes[idx // ncols][idx % ncols].axis("off")

    fig.suptitle("Cumulative Risk Decomposition by Departure Time",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    save_fig(fig, out_dir, "figA2_risk_decomposition_timeslots.png")


def fig_a3(records: Dict[str, Dict[str, Any]], out_dir: Path) -> None:
    """跨出发时刻的分量终值与构成占比（分量时变差异的定量对比）。"""
    keys = sorted(records.keys(), key=label_sort_key)
    labels = [display_label(k) for k in keys]

    finals = {k: np.array([_record_series(records[k])[c][-1] for c in COMPONENT_KEYS])
              for k in keys}
    totals = {k: float(finals[k].sum()) for k in keys}

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # ---------- (a) 分量终值分组柱 ----------
    ax = axes[0]
    x = np.arange(len(keys))
    width = 0.25
    for ci, comp in enumerate(COMPONENT_KEYS):
        vals = [finals[k][ci] for k in keys]
        bars = ax.bar(x + (ci - 1) * width, vals, width,
                      color=COMPONENT_COLORS[comp],
                      label=COMPONENT_LABELS[comp], alpha=0.9)
        ax.bar_label(bars, fmt="%.1e", fontsize=7, padding=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Final cumulative contribution")
    ax.set_title("(a) Component totals per departure time")
    ax.legend(fontsize=8)

    # ---------- (b) 构成占比 100% 堆积条 ----------
    ax = axes[1]
    y = np.arange(len(keys))
    left = np.zeros(len(keys))
    for comp in COMPONENT_KEYS:
        vals = np.array([finals[k][COMPONENT_KEYS.index(comp)] / totals[k] * 100.0
                         if totals[k] > 0 else 0.0 for k in keys])
        ax.barh(y, vals, left=left, color=COMPONENT_COLORS[comp],
                label=COMPONENT_LABELS[comp], alpha=0.9)
        for yi, (l, v) in enumerate(zip(left, vals)):
            if v > 4:
                ax.text(l + v / 2, yi, f"{v:.0f}%", ha="center", va="center",
                        fontsize=8, color="white", fontweight="bold")
        left += vals
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Share of total accumulated risk (%)")
    ax.set_title("(b) Risk composition share")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=8)

    fig.suptitle("Component-wise Accumulated Risk Across Departure Times",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_fig(fig, out_dir, "figA3_risk_composition_summary.png")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="缺口1 沿路径累积风险分量分解图")
    parser.add_argument("--paths", type=Path, default=EXP1_PATHS,
                        help="含逐步 states 的 paths.json（exp1 格式）")
    parser.add_argument("--out", type=Path,
                        default=OUTPUT_BASE / "risk_decomposition",
                        help="输出目录")
    args = parser.parse_args(argv)

    setup_style()
    print("=" * 60)
    print("Risk Decomposition Along Path (gap #1)")
    print("=" * 60)
    print(f"  Data: {args.paths}")

    records = load_path_records(args.paths)
    missing = [k for k, r in records.items() if not r["states"]]
    if missing:
        print(f"  [WARN] 跳过无 states 的记录: {missing}")
    records = {k: r for k, r in records.items() if r["states"]}
    if not records:
        raise SystemExit("没有可用的逐步 states 数据，无法生成分解图")

    print(f"  Records: {sorted(records.keys(), key=label_sort_key)}")
    fig_a1(records, args.out)
    fig_a2(records, args.out)
    fig_a3(records, args.out)


if __name__ == "__main__":
    main()
