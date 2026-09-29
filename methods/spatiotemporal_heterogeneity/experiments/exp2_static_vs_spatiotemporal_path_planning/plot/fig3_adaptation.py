#!/usr/bin/env python3
"""Figure 3：适应性曲线 —— 存活率/风险随出发时刻的变化（含安全后悔值）。

看点：static/distance 的路径固定，其真实风险随时段起伏（有的时段很危险）；
时空感知方法随时刻换路，存活率曲线更平稳且更优。
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_metrics import METHODS, METHOD_LABELS

COLORS = {"distance_only": "tab:blue", "static_risk": "tab:orange", "spatiotemporal": "tab:green"}
MARKERS = {"distance_only": "s", "static_risk": "^", "spatiotemporal": "o"}


def plot_fig3(evaluated: dict, hours, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), layout="constrained")
    fig.suptitle("Figure 3 — Adaptation to departure time: a static risk map cannot adapt", fontsize=12.5)

    ax = axes[0]
    for method in METHODS:
        ys = [evaluated.get(method, {}).get(h, {}).get("survival", float("nan")) for h in hours]
        ax.plot(hours, ys, marker=MARKERS[method], color=COLORS[method],
                lw=2.0, label=METHOD_LABELS[method])
    ax.set_xlabel("departure hour")
    ax.set_ylabel("survival $P_{surv}$ (true field)")
    ax.set_xticks(hours, [f"{h:02d}:00" for h in hours])
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    ax = axes[1]
    for method in METHODS:
        ys = [evaluated.get(method, {}).get(h, {}).get("cum_hazard", float("nan")) for h in hours]
        ax.plot(hours, ys, marker=MARKERS[method], color=COLORS[method],
                lw=2.0, label=METHOD_LABELS[method])
    ax.set_xlabel("departure hour")
    ax.set_ylabel("cumulative hazard $H$ (true field)")
    ax.set_xticks(hours, [f"{h:02d}:00" for h in hours])
    ax.grid(alpha=0.3)
    ax.legend(fontsize=9)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
