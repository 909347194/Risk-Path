#!/usr/bin/env python3
"""Figure 2：驱动因子 —— 风场（上排）与人口密度（下排）在 4 个时刻的演化。"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_fig2(grid, wind_4d, rho_pop, hours, z_layer, out_path):
    wmax = float(np.percentile(wind_4d[:, :, z_layer, :], 99)) or 1.0
    pmax = float(np.percentile(rho_pop, 99)) or 1.0

    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5), layout="constrained")
    fig.suptitle("Figure 2 — Drivers of spatiotemporal heterogeneity: "
                 "wind speed & population density", fontsize=13)
    for j, h in enumerate(hours):
        t_idx = grid.get_time_index(h)
        imw = axes[0, j].imshow(wind_4d[:, :, z_layer, t_idx].T, origin="lower",
                                cmap="viridis", vmin=0, vmax=wmax)
        axes[0, j].set_title(f"wind @ {h:02d}:00")
        # 人口热点位置标注（直观展示昼夜潮汐位移）
        slab = rho_pop[:, :, t_idx]
        px, py = np.unravel_index(np.argmax(slab), slab.shape)
        imp = axes[1, j].imshow(slab.T, origin="lower", cmap="YlOrRd", vmin=0, vmax=pmax)
        axes[1, j].plot(px, py, "b*", ms=11)
        axes[1, j].set_title(f"population @ {h:02d}:00\npeak at ({px},{py})")
        for i in (0, 1):
            axes[i, j].set_xlabel("x (grid)")
            axes[i, j].set_ylabel("y (grid)")
    fig.colorbar(imw, ax=axes[0, :], shrink=0.85, pad=0.02, label="m/s")
    fig.colorbar(imp, ax=axes[1, :], shrink=0.85, pad=0.02, label="density")
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
