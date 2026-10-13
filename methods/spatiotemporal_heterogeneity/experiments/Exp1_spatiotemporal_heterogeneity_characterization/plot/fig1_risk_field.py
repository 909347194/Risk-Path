#!/usr/bin/env python3
"""Figure 1：时空风险场 + 出发时刻路径响应（判读性重构版，2026-10-13）。

旧版问题（复盘）：四面板共用绝对色标 + 四条同色路径互相遮挡，风险场与路径的
时刻差异均不可见，读者第一印象是「什么都没变」。重构后面板分工：
  (a) 时间均值风险场 + 全部路径叠画（颜色+线型区分），标注最大分歧段窗口；
  (b) 最大分歧段局部放大 —— 「路径差在哪、差多少」直接可见；
  (c) 路径两两平均偏离矩阵（m）+ 格对角线判定口径；
  (d) 时间变异地图：逐格相对极差 (max−min)/mean（全 96 时相）；
  (e) ΔP_crash(t_h − 时间均值) × n：发散色标，展示风险空间重分布与各出发
      路径落在重分布的哪一侧。
注意：旧口径产物 fig1_risk_field_obvious.png 已废弃，不可与本图并列引用。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.patches import Rectangle

from exp_common import fmt_hour
from exp_planning import path_xy, path_cells_m, mean_deviation_m

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
          "#e377c2", "#7f7f7f"]
LINES = ["-", "--", "-.", (0, (5, 1))]


def _pairwise_dev_mat(cells: dict):
    """两两平均偏离矩阵（m）。cells: hour → (n,2) 物理坐标。"""
    hrs = sorted(cells)
    n = len(hrs)
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = mean_deviation_m(cells[hrs[i]], cells[hrs[j]])
            mat[i, j] = mat[j, i] = d
    return mat, hrs


def plot_fig1(grid, p_crash, results, hours, z_layer, od, out_path):
    hours = list(hours)
    ok = [(h, r) for h, r in zip(hours, results)
          if r.get("status") == "success" and r.get("path")]
    dx = float(grid.spatial.dx)
    cell_diag = float(np.hypot(dx, float(grid.spatial.dy)))

    # ---- 场统计 ----
    slab = p_crash[:, :, z_layer, :]                 # (nx, ny, nt)
    mean_field = slab.mean(axis=-1)
    rel_range = (slab.max(axis=-1) - slab.min(axis=-1)) / np.maximum(mean_field, 1e-12)

    fig = plt.figure(figsize=(19.0, 11.0), layout="constrained")
    gs = fig.add_gridspec(2, 4, height_ratios=[1.12, 0.92])
    ax_main = fig.add_subplot(gs[0, 0:2])
    ax_zoom = fig.add_subplot(gs[0, 2])
    ax_mat = fig.add_subplot(gs[0, 3])

    # ========== (a) 时间均值风险场 + 路径叠画 ==========
    vmax = max(float(np.percentile(mean_field, 99)), 1e-6)
    ax_main.imshow(mean_field.T, origin="lower", cmap="inferno",
                   vmin=0, vmax=vmax)
    paths_xy = {}
    for i, (h, res) in enumerate(ok):
        xs, ys = path_xy(res)
        if not xs:
            continue
        paths_xy[h] = np.column_stack([xs, ys]).astype(float)
        ax_main.plot(xs, ys, color=COLORS[i % len(COLORS)],
                     ls=LINES[i % len(LINES)], lw=2.0,
                     label=f"{fmt_hour(h)}  L={res['total_distance']:.0f} m")
    ax_main.plot(od[0], od[1], "o", color="lime", ms=9, mec="k", label="start")
    ax_main.plot(od[3], od[4], "*", color="red", ms=13, mec="k", label="goal")
    ax_main.set_xlabel("x (grid)")
    ax_main.set_ylabel("y (grid)")
    ax_main.legend(loc="upper right", fontsize=8, framealpha=0.85)
    ax_main.set_title("(a) time-mean $P_{crash}$ field + planned paths "
                      "by departure time", fontsize=11)

    # ---- 最大分歧段定位（网格坐标；口径与 mean_deviation_m 一致）----
    zoom_pt, zoom_dev_g = None, -1.0
    hrs_xy = sorted(paths_xy)
    for i in range(len(hrs_xy)):
        for j in range(i + 1, len(hrs_xy)):
            a, b = paths_xy[hrs_xy[i]], paths_xy[hrs_xy[j]]
            d = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1))
            mn = d.min(axis=1)
            k = int(np.argmax(mn))
            if mn[k] > zoom_dev_g:
                zoom_dev_g, zoom_pt = float(mn[k]), a[k].copy()

    half = 9
    if zoom_pt is not None:
        x0, x1 = zoom_pt[0] - half, zoom_pt[0] + half
        y0, y1 = zoom_pt[1] - half, zoom_pt[1] + half
        ax_main.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False,
                                    ec="white", lw=1.6, ls="--"))

    # ========== (b) 最大分歧段放大 ==========
    ax_zoom.imshow(mean_field.T, origin="lower", cmap="inferno",
                   vmin=0, vmax=vmax, alpha=0.55)   # 背景淡化，突出路径
    for i, (h, res) in enumerate(ok):
        xs, ys = path_xy(res)
        if xs:
            ax_zoom.plot(xs, ys, color=COLORS[i % len(COLORS)],
                         ls=LINES[i % len(LINES)], lw=2.4)
    if zoom_pt is not None:
        ax_zoom.set_xlim(x0, x1)
        ax_zoom.set_ylim(y0, y1)
        ax_zoom.set_title(
            "(b) zoom @ max pairwise divergence\n"
            f"separation ≈ {zoom_dev_g:.1f} cells ({zoom_dev_g * dx:.0f} m)",
            fontsize=10)
    else:
        ax_zoom.set_title("(b) zoom (no divergence found)", fontsize=10)
    ax_zoom.set_xlabel("x (grid)")

    # ========== (c) 路径两两平均偏离矩阵 ==========
    cells = {h: path_cells_m(res, grid) for h, res in ok}
    if len(cells) >= 2:
        mat, hrs_m = _pairwise_dev_mat(cells)
        im_m = ax_mat.imshow(mat, cmap="YlOrRd", vmin=0.0,
                             vmax=max(float(np.nanmax(mat)), 1e-6))
        for i in range(len(hrs_m)):
            for j in range(len(hrs_m)):
                ax_mat.text(j, i, f"{mat[i, j]:.1f}", ha="center", va="center",
                            fontsize=9,
                            color="white" if mat[i, j] > mat.max() * 0.6 else "black")
        ax_mat.set_xticks(range(len(hrs_m)))
        ax_mat.set_xticklabels([fmt_hour(h) for h in hrs_m],
                               fontsize=8, rotation=45)
        ax_mat.set_yticks(range(len(hrs_m)))
        ax_mat.set_yticklabels([fmt_hour(h) for h in hrs_m], fontsize=8)
        ax_mat.set_title("(c) pairwise mean deviation (m)\n"
                         f"cell diagonal = {cell_diag:.0f} m "
                         "(corridor-switch rule)", fontsize=10)
        fig.colorbar(im_m, ax=ax_mat, shrink=0.85, label="m")
        max_dev = float(np.nanmax(mat))
    else:
        ax_mat.set_title("(c) pairwise deviation (needs ≥2 paths)", fontsize=10)
        max_dev = float("nan")

    # ========== (d)(e) 下排：时间变异地图 + Δ 差值面板 ==========
    sub = gs[1, :].subgridspec(1, len(ok) + 1)
    ax_var = fig.add_subplot(sub[0, 0])
    rv = max(float(np.percentile(rel_range, 99)), 1e-9)
    im_v = ax_var.imshow(rel_range.T, origin="lower", cmap="magma",
                         vmin=0, vmax=rv)
    ax_var.set_title("(d) temporal variability\n"
                     "$(\\max_t-\\min_t)/\\mu_t$, all slices", fontsize=10)
    ax_var.set_xlabel("x (grid)")
    ax_var.set_ylabel("y (grid)")
    fig.colorbar(im_v, ax=ax_var, shrink=0.85)

    deltas = []
    for h, res in ok:
        t_idx = grid.get_time_index(h)
        deltas.append(p_crash[:, :, z_layer, t_idx] - mean_field)
    if deltas:
        v = max(float(np.percentile(np.abs(np.stack(deltas)), 98)), 1e-12)
        delta_axes, ims = [], []
        for i, ((h, res), dl) in enumerate(zip(ok, deltas)):
            axd = fig.add_subplot(sub[0, i + 1])
            imd = axd.imshow(dl.T, origin="lower", cmap="RdBu_r",
                             norm=TwoSlopeNorm(vmin=-v, vcenter=0.0, vmax=v))
            xs, ys = path_xy(res)
            if xs:
                axd.plot(xs, ys, color="k", lw=1.6)
            axd.set_title(f"(e{i + 1}) $\\Delta P_{{crash}}$ @ {fmt_hour(h)}\n"
                          f"max|Δ|={np.abs(dl).max():.1e}", fontsize=9)
            axd.set_xlabel("x (grid)")
            ims.append(imd)
            delta_axes.append(axd)
        fig.colorbar(ims[-1], ax=delta_axes, shrink=0.8,
                     label="$\\Delta P_{crash}$ (vs time mean)")

    # ---- 总标题 / 判定注记 ----
    dev_note = (f"max pairwise mean deviation = {max_dev:.1f} m | "
                if max_dev == max_dev else "")
    fig.suptitle(
        "Figure 1 — Spatiotemporal risk field & departure-time path response\n"
        f"same OD ({od[0]},{od[1]})→({od[3]},{od[4]}), "
        f"z≈{(z_layer + 1) * grid.spatial.dz:.0f} m | {dev_note}"
        f"cell diagonal = {cell_diag:.0f} m (deviation > diagonal ⇒ corridor switch)",
        fontsize=12)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"[fig1] saved {out_path}")
