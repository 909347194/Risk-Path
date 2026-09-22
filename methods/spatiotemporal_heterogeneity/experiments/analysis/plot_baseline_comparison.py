"""
缺口4 — 基线方法系统对比图（Baseline Comparison）

现有覆盖只有 CSV 数字（exp5_comprehensive/baseline_comparison.csv），缺少
系统对比图。本脚本补齐"风险质量 + 计算效率 + 综合画像 + 相对改进"四视角，
支撑核心主张：TD-RiskA* 在风险质量上系统性优于基线，且计算开销可接受。

对比算法：
  TD-RiskA*     —— 本文方法（完整时空风险）
  Static A*     —— 时间平均静态风险场基线
  Distance-only —— 纯距离最短路基线（不计风险）

数据源：results/exp5_comprehensive/{baseline_comparison,statistical_significance}.csv

产出（results/analysis_figures/baseline_comparison/）：
- figC1_baseline_quality.png     存活/致死/噪声 + 相对改进热力图
- figC2_baseline_efficiency.png  运行时间/搜索节点/路径长度 + 综合雷达
- baseline_summary.csv           各算法均值指标与相对改进（数据留档）

用法：
    python plot_baseline_comparison.py [--baseline CSV] [--out OUT_DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (  # noqa: E402
    ALGO_COLORS,
    ALGO_ORDER,
    EXP5_BASELINE,
    METRIC_DIRECTION,
    OUTPUT_BASE,
    improvement_pct,
    load_baseline_rows,
    load_significance,
    save_fig,
    setup_style,
)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402


def _grouped_bars(ax, od_order: List[str], per_algo: Dict[str, Dict[str, np.ndarray]],
                  metric: str, title: str, ylabel: str, log: bool = False,
                  symlog: bool = False, sig=None) -> None:
    """按 OD × 算法的分组柱状图（TD-RiskA* 可带显著性实验误差棒）。"""
    x = np.arange(len(od_order))
    n_algos = len(ALGO_ORDER)
    width = 0.8 / n_algos

    for ai, algo in enumerate(ALGO_ORDER):
        values = per_algo[algo][metric]
        offset = (ai - (n_algos - 1) / 2) * width
        ax.bar(x + offset, values, width, label=algo,
               color=ALGO_COLORS[algo], alpha=0.9, edgecolor="white")

        if algo == "TD-RiskA*" and sig is not None:
            errs = [sig.get((od, metric), {}).get("std", 0.0) for od in od_order]
            if any(e > 0 for e in errs):
                ax.errorbar(x + offset, values, yerr=errs, fmt="none",
                            ecolor="black", capsize=2, linewidth=1)

    if log:
        ax.set_yscale("log")
    if symlog:
        ax.set_yscale("symlog", linthresh=1e-6)

    ax.set_xticks(x)
    ax.set_xticklabels(od_order, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)


def fig_c1(od_order: List[str], categories: Dict[str, str],
           per_algo: Dict[str, Dict[str, np.ndarray]], sig, out_dir: Path) -> None:
    """风险质量对比 + 相对改进热力图。"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    _grouped_bars(axes[0][0], od_order, per_algo, "final_survival",
                  "(a) Final survival probability", "Survival probability", sig=sig)
    axes[0][0].set_ylim(0, 1.05)

    _grouped_bars(axes[0][1], od_order, per_algo, "cum_fatality",
                  "(b) Cumulative expected fatality", "Cumulative fatality",
                  symlog=True)

    _grouped_bars(axes[1][0], od_order, per_algo, "cum_noise",
                  "(c) Cumulative noise cost", "Cumulative noise", symlog=True)

    # ---------- (d) 相对改进热力图 ----------
    ax = axes[1][1]
    metrics = ["final_survival", "cum_fatality", "cum_noise"]
    baselines = ["Static A*", "Distance-only"]
    col_labels = [f"{m.replace('cum_', '').replace('final_', '').capitalize()} vs\n{b}"
                  for m in metrics for b in baselines]

    img = np.full((len(od_order), len(col_labels)), np.nan)
    for ri, od in enumerate(od_order):
        ci = 0
        for metric in metrics:
            td_val = per_algo["TD-RiskA*"][metric][ri]
            for base in baselines:
                base_val = per_algo[base][metric][ri]
                img[ri, ci] = improvement_pct(
                    td_val, base_val, METRIC_DIRECTION[metric])
                ci += 1

    cmap = LinearSegmentedColormap.from_list(
        "improve", ["#C0392B", "#F5B7B1", "#FFFFFF", "#ABEBC6", "#27AE60"])
    vmax = max(20.0, np.nanmax(np.abs(img)) if np.isfinite(img).any() else 20.0)
    im = ax.imshow(img, cmap=cmap, vmin=-vmax, vmax=vmax, aspect="auto")

    for ri in range(img.shape[0]):
        for ci in range(img.shape[1]):
            value = img[ri, ci]
            if np.isfinite(value):
                color = "white" if abs(value) > vmax * 0.55 else "black"
                ax.text(ci, ri, f"{value:+.0f}%", ha="center", va="center",
                        fontsize=7.5, color=color)
            else:
                ax.text(ci, ri, "n/a", ha="center", va="center",
                        fontsize=7.5, color="#7F8C8D")

    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, fontsize=7.5)
    ax.set_yticks(range(len(od_order)))
    ax.set_yticklabels([f"{od} ({categories.get(od, '')})" for od in od_order],
                       fontsize=8)
    ax.grid(False)
    ax.set_title("(d) TD-RiskA* improvement over baselines (positive = better)")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Improvement (%)")

    fig.suptitle("Baseline Comparison — Risk Quality (10 OD pairs)",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    save_fig(fig, out_dir, "figC1_baseline_quality.png")


def fig_c2(od_order: List[str], per_algo: Dict[str, Dict[str, np.ndarray]],
           sig, out_dir: Path) -> None:
    """计算效率对比 + 综合雷达画像。"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    _grouped_bars(axes[0][0], od_order, per_algo, "runtime_ms",
                  "(a) Runtime", "Runtime (ms, log)", log=True, sig=sig)
    _grouped_bars(axes[0][1], od_order, per_algo, "nodes_explored",
                  "(b) Search effort", "Nodes explored (log)", log=True)
    _grouped_bars(axes[1][0], od_order, per_algo, "path_length",
                  "(c) Path length", "Path length (m)", sig=sig)

    # ---------- (d) 综合雷达（均值指标归一化，越大越好） ----------
    ax = axes[1][1]
    ax.remove()
    ax = fig.add_subplot(2, 2, 4, polar=True)

    radar_metrics = ["final_survival", "cum_fatality", "cum_noise",
                     "path_length", "runtime_ms", "nodes_explored"]
    labels = ["Survival", "1-Fatality", "1-Noise", "Path len.", "Runtime", "Nodes"]
    n = len(radar_metrics)

    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]

    for algo in ALGO_ORDER:
        values = []
        for metric in radar_metrics:
            mean_val = float(np.nanmean(per_algo[algo][metric]))
            all_means = [float(np.nanmean(per_algo[a][metric])) for a in ALGO_ORDER]
            lo, hi = min(all_means), max(all_means)
            benefit = mean_val if METRIC_DIRECTION[metric] else -mean_val
            benefit_lo = lo if METRIC_DIRECTION[metric] else -hi
            benefit_hi = hi if METRIC_DIRECTION[metric] else -lo
            if benefit_hi > benefit_lo:
                values.append((benefit - benefit_lo) / (benefit_hi - benefit_lo))
            else:
                values.append(0.5)
        values += values[:1]
        ax.plot(angles, values, color=ALGO_COLORS[algo], linewidth=2, label=algo)
        ax.fill(angles, values, color=ALGO_COLORS[algo], alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=7)
    ax.set_title("(d) Normalized mean profile (outer = better)",
                 fontsize=11, pad=16)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=8)

    fig.suptitle("Baseline Comparison — Efficiency & Overall Profile",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.tight_layout()
    save_fig(fig, out_dir, "figC2_baseline_efficiency.png")


def export_summary(od_order: List[str], per_algo: Dict[str, Dict[str, np.ndarray]],
                   out_dir: Path) -> None:
    """各算法均值指标 + TD-RiskA* 相对改进，CSV 留档。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = ["path_length", "final_survival", "cum_fatality", "cum_noise",
               "runtime_ms", "nodes_explored"]
    header = ["algorithm", "metric", "mean", "improvement_vs_StaticA_pct",
              "improvement_vs_DistanceOnly_pct"]
    lines = [",".join(header)]
    for algo in ALGO_ORDER:
        for metric in metrics:
            mean_val = float(np.nanmean(per_algo[algo][metric]))
            imp_static = improvement_pct(
                mean_val,
                float(np.nanmean(per_algo["Static A*"][metric])),
                METRIC_DIRECTION[metric]) if algo == "TD-RiskA*" else float("nan")
            imp_dist = improvement_pct(
                mean_val,
                float(np.nanmean(per_algo["Distance-only"][metric])),
                METRIC_DIRECTION[metric]) if algo == "TD-RiskA*" else float("nan")
            lines.append(",".join([
                algo, metric, f"{mean_val:.8g}",
                "" if not np.isfinite(imp_static) else f"{imp_static:.3f}",
                "" if not np.isfinite(imp_dist) else f"{imp_dist:.3f}",
            ]))
    target = out_dir / "baseline_summary.csv"
    target.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [OK] Saved: {target}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="缺口4 基线方法系统对比图")
    parser.add_argument("--baseline", type=Path, default=EXP5_BASELINE,
                        help="baseline_comparison.csv 路径")
    parser.add_argument("--out", type=Path,
                        default=OUTPUT_BASE / "baseline_comparison",
                        help="输出目录")
    args = parser.parse_args(argv)

    setup_style()
    print("=" * 60)
    print("Baseline Comparison (gap #4)")
    print("=" * 60)
    print(f"  Data: {args.baseline}")

    od_order, per_algo = load_baseline_rows(args.baseline)
    categories = {od: str(per_algo["TD-RiskA*"]["category"][i])
                  for i, od in enumerate(od_order)}
    missing = [a for a in ALGO_ORDER if a not in per_algo]
    if missing:
        raise SystemExit(f"baseline_comparison.csv 缺少算法列: {missing}")

    try:
        sig = load_significance()
    except FileNotFoundError:
        sig = {}
        print("  [WARN] 未找到 statistical_significance.csv，误差棒跳过")

    print(f"  OD pairs: {od_order}")
    fig_c1(od_order, categories, per_algo, sig, args.out)
    fig_c2(od_order, per_algo, sig, args.out)
    export_summary(od_order, per_algo, args.out)


if __name__ == "__main__":
    main()
