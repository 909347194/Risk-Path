#!/usr/bin/env python3
"""Figure 1：四时刻风险场（P_crash）+ 同一 OD 的规划路径。"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import path_xy


def plot_fig1(grid, p_crash, results, hours, z_layer, od, out_path):
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-6)

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.5), layout="constrained")
    fig.suptitle(
        "Figure 1 — Spatiotemporal risk field $P_{crash}(x,y,z,t)$ and optimal path\n"
        f"same OD ({od[0]},{od[1]}) -> ({od[3]},{od[4]}) at z≈{(z_layer+1)*grid.spatial.dz:.0f} m; "
        "different departure time -> different risk landscape -> different path",
        fontsize=13,
    )
    im = None
    for ax, h, res in zip(axes.flat, hours, results):
        t_idx = grid.get_time_index(h)
        im = ax.imshow(p_crash[:, :, z_layer, t_idx].T, origin="lower",
                       cmap="inferno", vmin=0, vmax=vmax)
        xs, ys = path_xy(res)
        if xs:
            ax.plot(xs, ys, color="cyan", lw=2.0,
                    label=f"path L={res['total_distance']:.0f} m")
            ax.plot(xs[0], ys[0], "o", color="lime", ms=9, label="start")
            ax.plot(xs[-1], ys[-1], "*", color="red", ms=13, label="goal")
        ok = res.get("status") == "success"
        ax.set_title(
            f"{h:02d}:00  $P_{{surv}}$={res.get('final_p_survival', float('nan')):.4f}"
            if ok else f"{h:02d}:00  (failed: {res.get('reason')})", fontsize=11)
        ax.set_xlabel("x (grid)")
        ax.set_ylabel("y (grid)")
        if xs:
            ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("$P_{crash}$")
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
