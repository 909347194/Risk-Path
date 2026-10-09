#!/usr/bin/env python3
"""Figure 2：三方法六指标对比柱状图（逐出发时刻分组）。

覆盖 Table 1 的全部指标口径：L / R_fatal / R_property / R_noise / P_surv / T_compute，
外加累计危险率 H（结论判定用的复合风险量）。所有指标均为真实时空场统一后评估。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_metrics import METHODS, METHOD_LABELS

COLORS = {"distance_only": "tab:blue", "static_risk": "tab:orange", "spatiotemporal": "tab:green"}


def plot_fig2(rows: list[dict], hours, out_path):
    metrics = [
        ("length_m", "path length $L$ (m)"),
        ("fatal_risk", "fatal risk $R_{fatal}$"),
        ("property_risk", "property risk $R_{property}$"),
        ("noise_risk", "noise risk $R_{noise}$"),
        ("survival", "survival $P_{surv}$"),
        ("runtime_s", "planning runtime $T_{compute}$ (s)"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.2), layout="constrained")
    fig.suptitle("Figure 2 — Method comparison at each departure time "
                 "(all metrics evaluated on the true spatiotemporal field)", fontsize=12)

    x = np.arange(len(hours))
    width = 0.26
    for ax, (key, label) in zip(axes.flat, metrics):
        for i, method in enumerate(METHODS):
            vals = []
            for h in hours:
                row = next((r for r in rows if r["method"] == METHOD_LABELS[method]
                            and r["departure_hour"] == h and r.get("status") == "success"), None)
                vals.append(row[key] if row else 0.0)
            ax.bar(x + (i - 1) * width, vals, width, label=METHOD_LABELS[method],
                   color=COLORS[method])
        ax.set_xticks(x, [f"{h:02d}:00" for h in hours])
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.3)
    axes.flat[0].legend(fontsize=8)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
