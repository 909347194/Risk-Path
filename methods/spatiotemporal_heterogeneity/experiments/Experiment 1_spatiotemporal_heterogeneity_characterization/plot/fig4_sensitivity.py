#!/usr/bin/env python3
"""Figure 4：权重敏感性 —— 三种 regime 与「路径随时刻变化」的稳健性。"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_fig4(rows, hours, out_path):
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), layout="constrained")
    ratios = [r["ratio"] for r in rows]
    spread = [r["spread_m"] for r in rows]

    ax0 = axes[0]
    ax0.plot(ratios, spread, "o-", color="darkslateblue", lw=2)
    for x, y in zip(ratios, spread):
        ax0.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=8)
    ax0.set_xlabel("risk aversion  $w_{fatal}/w_{ops}$")
    ax0.set_ylabel("path length spread across departure times (m)")
    ax0.set_title("(a) Spread vs risk aversion (three regimes)")
    ax0.grid(alpha=0.3)

    ax1 = axes[1]
    markers = ["o", "s", "^", "D", "v"]
    for i, r in enumerate(rows):
        ax1.plot(hours, [r[f"L_{h:02d}h"] for h in hours], marker=markers[i % len(markers)],
                 lw=1.8, label=f"ratio={r['ratio']:.0f} (spread {r['spread_m']:.0f} m)")
    ax1.set_xlabel("departure hour")
    ax1.set_ylabel("path length (m)")
    ax1.set_title("(b) Path length vs departure hour, per risk aversion")
    ax1.set_xticks(hours)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    fig.suptitle("Figure 4 — Weight sensitivity: path response to departure time "
                 "is regime-dependent (not a single cherry-picked weight)", fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
