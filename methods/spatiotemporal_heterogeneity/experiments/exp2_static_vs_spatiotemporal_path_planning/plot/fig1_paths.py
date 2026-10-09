#!/usr/bin/env python3
"""Figure 1（论文 Figure 2）：三种方法的路径 × 四个出发时刻（叠加真实 P_crash 切片）。

看点（一眼可见）：same OD + different departure time + different risk model
→ different route decisions：
  static/distance 路径不依赖出发时刻（四面板同一条线），时空感知路径随时刻调整；
  每个面板标注 D(P_static,P_ST) 与 path-change rate（路径决策差异的定量证据）。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import (path_xy, path_cells_m, mean_deviation_m,
                          path_change_rate)

STYLES = {
    "distance_only": dict(color="tab:blue", ls="--", lw=1.8, label="Distance-only A*"),
    "static_risk": dict(color="tab:orange", ls=":", lw=2.2, label="Static-Risk A*"),
    "spatiotemporal": dict(color="cyan", ls="-", lw=2.2, label="Spatiotemporal A* (ours)"),
}


def plot_fig1(grid, p_crash, evaluated_paths, hours, z_layer, od, out_path):
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-9)
    cell_diag = float(np.hypot(grid.spatial.dx, grid.spatial.dy))

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.0), layout="constrained")
    fig.suptitle(
        "Figure 1 — same OD + different departure time + different risk model "
        "-> different route decisions\n"
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

        # 定量标注：静态 vs 时空的路径决策差异（D 与 change-rate 口径见 exp_planning）
        cells = {m: path_cells_m(res, grid) for m, res in evaluated_paths[h].items()}
        a, b = cells.get("static_risk"), cells.get("spatiotemporal")
        if a is not None and b is not None and len(a) > 0 and len(b) > 0:
            dev = mean_deviation_m(a, b)
            chg = path_change_rate(a, b, cell_diag)
            ax.text(0.02, 0.025,
                    f"$D(P_{{static}},P_{{ST}})$ = {dev:.0f} m\n"
                    f"path-change rate = {chg:.2f}",
                    transform=ax.transAxes, fontsize=8.5, color="white",
                    va="bottom", ha="left",
                    bbox=dict(boxstyle="round,pad=0.35", fc="black", alpha=0.55))
        ax.legend(loc="upper right", fontsize=8, framealpha=0.85)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
