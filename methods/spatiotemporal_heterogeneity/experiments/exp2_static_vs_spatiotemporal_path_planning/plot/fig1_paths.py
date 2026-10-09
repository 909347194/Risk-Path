#!/usr/bin/env python3
"""Figure 1（论文 Figure 2）：三种方法的路径 × 四个出发时刻（叠加真实 P_crash 切片）。

看点（一眼可见）：same OD + different departure time + different risk model
→ different route decisions：
  - static/distance 路径不依赖出发时刻（四面板同一条线），时空感知路径随时刻调整；
  - 每个面板标注 D(P_static,P_ST) 与 path-change rate（路径决策差异的定量证据）；
  - ST 路径上偏离 static 走廊（>1 格对角线）的区段用洋红点标出（差异的位置）。

布局约定：全局单图例（figure 级，避免 4 面板重复）、共享色条、仅外侧
行列标注坐标轴，统计标注固定放右上角（OD 走廊为左上→右下对角线，右上角
不与路径相交）。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_planning import (path_xy, path_cells_m, mean_deviation_m,
                          path_change_rate)
from plot.style import (DEVIATION_COLOR, LINEWIDTHS, line_style,
                        method_legend_handles, deviation_legend_handle)


def _deviating_mask(cells_st: np.ndarray, cells_static: np.ndarray,
                    cell_diag: float) -> np.ndarray:
    """ST 路径上到 static 路径最近点 > cell_diag 的采样点掩码（决策差异位置）。"""
    if len(cells_st) == 0 or len(cells_static) == 0:
        return np.zeros(0, dtype=bool)
    d = np.sqrt(((cells_st[:, None, :] - cells_static[None, :, :]) ** 2).sum(-1))
    return d.min(axis=1) > cell_diag


def plot_fig1(grid, p_crash, evaluated_paths, hours, z_layer, od, out_path):
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-9)
    cell_diag = float(np.hypot(grid.spatial.dx, grid.spatial.dy))
    z_m = (z_layer + 1) * grid.spatial.dz

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.0), layout="constrained")
    fig.suptitle(
        "Figure 1 (paper Figure 2) — same OD, different departure time, "
        "different risk model: route decisions\n"
        f"OD ({od[0]},{od[1]}) → ({od[3]},{od[4]}), flight altitude z≈{z_m:.0f} m; "
        "background = true $P_{crash}(x,y,t)$ at the departure slice",
        fontsize=12.5,
    )

    im = None
    dev_drawn = False
    for i, (ax, h) in enumerate(zip(axes.flat, hours)):
        row, col = divmod(i, axes.shape[1])
        t_idx = grid.get_time_index(h)
        im = ax.imshow(p_crash[:, :, z_layer, t_idx].T, origin="lower",
                       cmap="inferno", vmin=0, vmax=vmax)

        cells, failed = {}, []
        for method, res in evaluated_paths[h].items():
            xs, ys = path_xy(res)
            cells[method] = path_cells_m(res, grid)
            if xs:
                # 白色描边垫底：路径在 inferno 热力图（黑/紫/橙/黄）上始终可辨
                ax.plot(xs, ys, color="white", lw=LINEWIDTHS[method] + 1.8,
                        solid_capstyle="round", zorder=3)
                ax.plot(xs, ys, zorder=4, **line_style(method))
            else:
                failed.append(method)

        # ST 偏离 static 走廊的区段（路径决策差异的位置）
        mask = _deviating_mask(cells.get("spatiotemporal", np.zeros((0, 2))),
                               cells.get("static_risk", np.zeros((0, 2))),
                               cell_diag)
        if mask.any():
            st_cells = cells["spatiotemporal"]
            ax.scatter(st_cells[mask, 0], st_cells[mask, 1], s=18,
                       color=DEVIATION_COLOR, zorder=5,
                       edgecolors="white", linewidths=0.8)
            dev_drawn = True

        ax.plot(od[0], od[1], "o", color="lime", ms=9, mec="k", mew=1.2)
        ax.plot(od[3], od[4], "*", color="red", ms=13)

        title = f"{h:02d}:00"
        if failed:
            title += f"  (failed: {', '.join(failed)})"
        ax.set_title(title, fontsize=11)
        # 仅外侧行列标注坐标轴（共享坐标系，避免 4 份重复）
        if row == axes.shape[0] - 1:
            ax.set_xlabel("x (grid index)")
        if col == 0:
            ax.set_ylabel("y (grid index)")

        # 统计标注：右上角（OD 走廊为左上→右下，右上角不与路径相交）
        a, b = cells.get("static_risk"), cells.get("spatiotemporal")
        if a is not None and b is not None and len(a) > 0 and len(b) > 0:
            dev = mean_deviation_m(a, b)
            chg = path_change_rate(a, b, cell_diag)
            ax.text(0.98, 0.97,
                    f"$D(P_{{static}},P_{{ST}})$ = {dev:.0f} m\n"
                    f"path-change rate = {chg:.2f}",
                    transform=ax.transAxes, fontsize=8.5, color="white",
                    va="top", ha="right",
                    bbox=dict(boxstyle="round,pad=0.35", fc="black", alpha=0.75))

    # 全局单图例（放底部：顶部留给总标题，避免图例压字）
    handles = method_legend_handles()
    if dev_drawn:
        handles.append(deviation_legend_handle())
    fig.legend(handles=handles, loc="outside lower center", ncol=3,
               fontsize=9, framealpha=0.9)

    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("$P_{crash}$ (true spatiotemporal field)")

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
