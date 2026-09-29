#!/usr/bin/env python3
"""Figure 2：三方法指标对比柱状图（逐出发时刻分组）。"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_metrics import METHODS, METHOD_LABELS

COLORS = {"distance_only": "tab:blue", "static_risk": "tab:orange", "spatiotemporal": "tab:green"}


def plot_fig2(rows: list[dict], hours, out_path):
    metrics = [
        ("distance_m", "path length (m)"),
        ("risk_cum_hazard", "cumulative hazard $H$"),
        ("survival", "survival $P_{surv}$"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), layout="constrained")
    fig.suptitle("Figure 2 — Method comparison at each departure time "
                 "(all metrics evaluated on the true spatiotemporal field)", fontsize=12)

    x = np.arange(len(hours))
    width = 0.26
    for ax, (key, label) in zip(axes, metrics):
        for i, method in enumerate(METHODS):
            vals = []
            for h in hours:
                row = next((r for r in rows if r["method"] == method
                            and r["departure_hour"] == h and r.get("status") == "success"), None)
                vals.append(row[key] if row else 0.0)
            ax.bar(x + (i - 1) * width, vals, width, label=METHOD_LABELS[method],
                   color=COLORS[method])
        ax.set_xticks(x, [f"{h:02d}:00" for h in hours])
        ax.set_ylabel(label)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(fontsize=8)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
