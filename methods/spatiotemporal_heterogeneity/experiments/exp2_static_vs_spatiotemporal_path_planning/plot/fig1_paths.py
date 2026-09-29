#!/usr/bin/env python3
"""Figure 1：三种方法的路径 × 四个出发时刻（叠加在真实 P_crash 切片上）。

看点：static/distance 路径不随时变（四面板同一条线），时空感知路径随时刻调整。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import path_xy

STYLES = {
    "distance_only": dict(color="tab:blue", ls="--", lw=1.8, label="Distance-only A*"),
    "static_risk": dict(color="tab:orange", ls=":", lw=2.2, label="Static-Risk A*"),
    "spatiotemporal": dict(color="cyan", ls="-", lw=2.2, label="Spatiotemporal A* (ours)"),
}


def plot_fig1(grid, p_crash, evaluated_paths, hours, z_layer, od, out_path):
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-9)

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.0), layout="constrained")
    fig.suptitle(
        "Figure 1 — Static vs spatiotemporal planning: same OD, 4 departure times\n"
        f"OD ({od[0]},{od[1]}) -> ({od[3]},{od[4]}), z≈{(z_layer+1)*grid.spatial.dz:.0f} m; "
        "background = true $P_{crash}(x,y,t)$",
        fontsize=12.5,
    )
    for ax, h in zip(axes.flat, hours):
        t_idx = grid.get_time_index(h)
        ax.imshow(p_crash[:, :, z_layer, t_idx].T, origin="lower",
                  cmap="inferno", vmin=0, vmax=vmax)
        for method, res in evaluated_paths[h].items():
            xs, ys = path_xy(res)
            if xs:
                ax.plot(xs, ys, **STYLES[method])
        ax.plot(od[0], od[1], "o", color="lime", ms=9, label="start")
        ax.plot(od[3], od[4], "*", color="red", ms=13, label="goal")
        ax.set_title(f"{h:02d}:00", fontsize=11)
        ax.set_xlabel("x (grid)")
        ax.set_ylabel("y (grid)")
        ax.legend(loc="upper right", fontsize=8, framealpha=0.85)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
