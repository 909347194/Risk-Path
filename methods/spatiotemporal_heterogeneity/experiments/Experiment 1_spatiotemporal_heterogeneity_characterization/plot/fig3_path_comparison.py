#!/usr/bin/env python3
"""Figure 3：四条路径叠加对比 + 路径长度 / 存活率 柱状图。"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import path_xy


def plot_fig3(grid, results, hours, building, od, out_path):
    fig = plt.figure(figsize=(16.5, 5.6), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.0, 1.0])

    # (a) 四条路径叠加（背景：建筑高度，静态城市底图）
    ax0 = fig.add_subplot(gs[0, 0])
    b_vmax = float(np.percentile(building, 98)) or float(building.max()) or 1.0
    ax0.imshow(building.T, origin="lower", cmap="Greys",
               vmin=0, vmax=b_vmax, interpolation="nearest")
    colors = ["cyan", "orange", "lime", "magenta"]
    for h, res, c in zip(hours, results, colors):
        xs, ys = path_xy(res)
        if xs:
            ax0.plot(xs, ys, color=c, lw=2.2, label=f"{h:02d}:00  L={res['total_distance']:.0f} m")
    ax0.plot(od[0], od[1], "o", color="white", ms=10, mec="k", label="start")
    ax0.plot(od[3], od[4], "*", color="yellow", ms=15, mec="k", label="goal")
    ax0.set_title("(a) Planned paths for the same OD, 4 departure times")
    ax0.set_xlabel("x (grid)")
    ax0.set_ylabel("y (grid)")
    ax0.legend(loc="upper left", fontsize=8, framealpha=0.9)

    ok = [r for r in results if r.get("status") == "success"]
    ok_hours = [h for h, r in zip(hours, results) if r.get("status") == "success"]

    # (b) 路径长度
    ax1 = fig.add_subplot(gs[0, 1])
    L = [r["total_distance"] for r in ok]
    bars = ax1.bar([f"{h:02d}:00" for h in ok_hours], L, color="steelblue")
    ax1.set_title("(b) Path length vs departure time")
    ax1.set_ylabel("path length (m)")
    ax1.set_ylim(min(L) * 0.92 if L else 0, max(L) * 1.04 if L else 1)
    ax1.bar_label(bars, fmt="%.0f", fontsize=8)
    if L:
        ax1.axhline(min(L), ls="--", c="k", lw=1,
                    label=f"min {min(L):.0f} m")
        ax1.legend(fontsize=8)

    # (c) 存活率
    ax2 = fig.add_subplot(gs[0, 2])
    P = [r["final_p_survival"] for r in ok]
    bars2 = ax2.bar([f"{h:02d}:00" for h in ok_hours], P, color="indianred")
    ax2.set_title("(c) Survival probability vs departure time")
    ax2.set_ylabel("$P_{surv}$")
    ax2.set_ylim(0, max(P) * 1.25 if P else 1)
    ax2.bar_label(bars2, fmt="%.4f", fontsize=8)

    fig.suptitle("Figure 3 — Same OD, different departure time -> different optimal path",
                 fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
