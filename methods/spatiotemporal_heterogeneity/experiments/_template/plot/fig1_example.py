#!/usr/bin/env python3
"""示例图：替换为实验自己的图（改名 figN_<主题>.py，函数 plot_figN）。"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import path_xy


def plot_fig1(grid, field, results, hours, z_layer, od, out_path):
    """示例：某风险切片 + 路径叠加。按实验需要改签名与内容。"""
    fig, axes = plt.subplots(1, min(4, len(hours)), figsize=(4 * min(4, len(hours)), 4),
                             layout="constrained", squeeze=False)
    vmax = max(float(np.percentile(field[:, :, z_layer, :], 99)), 1e-6)
    for ax, h, res in zip(axes.flat, hours, results):
        t_idx = grid.get_time_index(h)
        ax.imshow(field[:, :, z_layer, t_idx].T, origin="lower", cmap="inferno",
                  vmin=0, vmax=vmax)
        xs, ys = path_xy(res)
        if xs:
            ax.plot(xs, ys, color="cyan", lw=2.0)
        ax.set_title(f"{h:02d}:00")
    fig.suptitle("Figure 1 — (示例图，替换为实验自己的图)")
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
