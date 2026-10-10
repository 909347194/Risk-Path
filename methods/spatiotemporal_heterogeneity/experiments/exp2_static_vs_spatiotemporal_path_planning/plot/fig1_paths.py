#!/usr/bin/env python3
"""Figure 1（论文 Figure 2）：三种方法的路径 × 四个出发时刻（叠加真实 P_crash 切片）。

看点（一眼可见）：same OD + different departure time + different risk model
→ different route decisions：
  - static / distance 路径不依赖出发时刻（四面板同一条线），时空感知路径随时刻调整；
  - 每个面板标注 D(P_static,P_ST) 与 path-change rate（路径决策差异的定量证据）。

布局约定（期刊级）：2×2 子图、去上/右边框、刻度朝外、共享色条、全局单图例
（底部）；子图角标 (a)–(d)；统计标注固定放右上角（OD 走廊左上→右下，右上角
不与路径相交），白底细框黑字，在 inferno 背景上始终可读。

路径绘制规范（参考 Exp1：单根实色线 + 简单标记，不复杂化）：
  - 三条路径：单根实色实线，差异靠颜色 + 线宽编码（ours 略粗）；
    不做黑描边 halo / 发光带等多层叠加；
  - 配色与暖色 inferno 背景强对比：Distance=青、Static=淡紫、ST(ours)=亮粉红；
  - 起点/终点：白填充 + 黑描边的几何标记（圆/星），暗背景清晰；
  - 差异位置由路径自身可见差异 + 统计框 D 值说明（不额外画散点/发光带）。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from exp_planning import (path_xy, path_cells_m, mean_deviation_m,
                          path_change_rate)
from exp_metrics import METHODS, METHOD_LABELS
from plot.style import panel_label

PANEL_LETTERS = ["a", "b", "c", "d"]

# —— 路径配色（适配 inferno 暗背景，冷色 + 亮粉红 our，参考 Exp1 简洁实线）——
PATH_COLORS = {
    "distance_only": "#22D3EE",   # 青  — Distance-only A*
    "static_risk":    "#A78BFA",   # 淡紫 — Static-Risk A*
    "spatiotemporal": "#FF4D8D",   # 亮粉红 — Spatiotemporal A* (ours)
}
PATH_LW = {"distance_only": 2.0, "static_risk": 2.2, "spatiotemporal": 2.6}
Z_CORE = 4

# 起点 / 终点：白填充 + 黑描边（任意背景清晰）
START_MFC, START_MEC = "white", "black"
GOAL_MFC, GOAL_MEC = "white", "black"


def plot_fig1(grid, p_crash, evaluated_paths, hours, z_layer, od, out_path):
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-9)
    cell_diag = float(np.hypot(grid.spatial.dx, grid.spatial.dy))
    z_m = (z_layer + 1) * grid.spatial.dz

    fig, axes = plt.subplots(2, 2, figsize=(11.5, 9.5), layout="constrained")
    fig.suptitle(
        "Figure 1 (paper Figure 2) — Same OD, different departure time, different "
        "risk model: route decisions\n"
        f"OD ({od[0]},{od[1]}) → ({od[3]},{od[4]}), flight altitude z≈{z_m:.0f} m; "
        "background = true $P_{crash}(x,y,t)$ at the departure slice",
        fontsize=11, fontweight="bold", x=0.5,
    )

    im = None
    for i, (ax, h) in enumerate(zip(axes.flat, hours)):
        t_idx = grid.get_time_index(h)
        im = ax.imshow(p_crash[:, :, z_layer, t_idx].T, origin="lower",
                       cmap="inferno", vmin=0, vmax=vmax)

        cells, failed = {}, []
        for method in METHODS:
            res = evaluated_paths[h].get(method)
            if res is None:
                failed.append(method)
                continue
            xs, ys = path_xy(res)
            cells[method] = path_cells_m(res, grid)
            if xs:
                # 单根实色实线（参考 Exp1：不做 halo / 发光带等多层叠加）
                ax.plot(xs, ys, color=PATH_COLORS[method], lw=PATH_LW[method],
                        solid_capstyle="round", zorder=Z_CORE)
            else:
                failed.append(method)

        # 起点 / 终点：白填充黑描边几何标记
        ax.plot(od[0], od[1], "o", ms=9, mfc=START_MFC, mec=START_MEC,
                mew=1.3, zorder=6)
        ax.plot(od[3], od[4], "*", ms=16, mfc=GOAL_MFC, mec=GOAL_MEC,
                mew=1.0, zorder=6)

        title = f"{h:02d}:00"
        if failed:
            title += f"  (failed: {', '.join(failed)})"
        ax.set_title(title, fontsize=10)
        panel_label(ax, PANEL_LETTERS[i])

        # 仅外侧行列标注坐标轴（共享坐标系，避免 4 份重复）
        if i >= axes.shape[1]:
            ax.set_xlabel("x (grid index)")
        if i % axes.shape[1] == 0:
            ax.set_ylabel("y (grid index)")

        # 统计标注：右上角（OD 走廊为左上→右下，右上角不与路径相交）
        a, b = cells.get("static_risk"), cells.get("spatiotemporal")
        if a is not None and b is not None and len(a) > 0 and len(b) > 0:
            dev = mean_deviation_m(a, b)
            chg = path_change_rate(a, b, cell_diag)
            ax.text(0.98, 0.98,
                    f"$D(P_{{\\mathrm{{static}}}},P_{{\\mathrm{{ST}}}})$ = {dev:.0f} m\n"
                    f"path-change rate = {chg:.2f}",
                    transform=ax.transAxes, fontsize=8, color="black",
                    va="top", ha="right",
                    bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#555",
                              alpha=0.9, lw=0.6))

    # 全局单图例（底部；顶部留给总标题，避免图例压字）
    handles = [Line2D([], [], color=PATH_COLORS[m], lw=PATH_LW[m],
                      label=METHOD_LABELS[m]) for m in METHODS]
    handles += [
        Line2D([], [], marker="o", ls="", color="white", ms=8, mec="black",
               mew=1.2, label="start"),
        Line2D([], [], marker="*", ls="", color="white", ms=14, mec="black",
               mew=1.0, label="goal"),
    ]
    fig.legend(handles=handles, loc="outside lower center", ncol=3,
               fontsize=9, framealpha=0.95, edgecolor="#888")

    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("$P_{crash}$  (true spatiotemporal field)")
        cbar.ax.tick_params(direction="out", width=0.8)

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
