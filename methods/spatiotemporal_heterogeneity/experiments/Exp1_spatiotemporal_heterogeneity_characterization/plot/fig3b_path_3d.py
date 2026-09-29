#!/usr/bin/env python3
"""Figure 3b：四条规划路径的三维可视化。

输入是 run.py 主流程已完成的规划结果 results（而非再跑一遍 planner）：
  (a) 3D 投影视图（x, y, 高度），直观展示路径在高度维的爬升/下降；
  (b) 平面俯视图（x-y）+ 建筑高度底图，与 fig3(a) 一致的坐标系；
  (c) 高度剖面（高度 vs 累计水平距离），定量呈现每条路径的 3D 起伏。

约定沿 fig3_path_comparison.py：cyan/orange/lime/magenta、Greys 建筑底图、
起点 white "o" / 终点 yellow "*"、constrained 布局、dpi 140。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 高度维在 3D 投影里相对水平范围（~1 km）很小，做可视化夸张以便看清爬升/下降
Z_EXAG = 6.0
COLORS = ["cyan", "orange", "lime", "magenta"]


def plot_fig3b(results, hours, od, building_heights, grid, out_path,
               stats_path=None):
    """从规划结果绘制 3D 路径图 + 导出高度维统计 CSV。

    results: plan_one 的返回值列表（与 hours 对齐；失败项自动跳过）。
    返回 (n_plotted, stats_rows)；stats_rows 同时写入 stats_path（若给定）。
    """
    dz = float(grid.spatial.dz)
    dx = float(getattr(grid.spatial, "dx", dz))
    dy = float(getattr(grid.spatial, "dy", dz))
    od = list(map(float, od))

    # ---- 收集数据 ----
    items = []
    for h, res, c in zip(hours, results, COLORS):
        if res.get("status") != "success" or not res.get("path"):
            continue
        coords = np.array([p["coords"] for p in res["path"]], dtype=float)
        xs, ys, zs = coords[:, 0], coords[:, 1], coords[:, 2].astype(int)
        alts = (zs + 1.0) * dz
        cum_h = np.concatenate([[0.0], np.cumsum(np.sqrt(
            (dx * np.diff(xs)) ** 2 + (dy * np.diff(ys)) ** 2))])
        L3d = float(np.sum(np.sqrt(
            (dx * np.diff(xs)) ** 2 + (dy * np.diff(ys)) ** 2
            + (dz * np.diff(zs)) ** 2)))
        items.append(dict(h=h, color=c, coords=coords, xs=xs, ys=ys, zs=zs,
                          alts=alts, cum_h=cum_h, L3d=L3d,
                          Lh=float(cum_h[-1]) if len(cum_h) else 0.0,
                          climb_total=int(np.abs(np.diff(zs)).sum()) if len(zs) > 1 else 0))
    if not items:
        print("[fig3b] 无成功路径可画，跳过")
        return 0, []

    # ---- 绘图 ----
    fig = plt.figure(figsize=(17.5, 5.8), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 1.15])

    # (a) 3D 投影
    ax0 = fig.add_subplot(gs[0, 0], projection="3d")
    for it in items:
        ax0.plot(it["xs"], it["ys"], it["alts"] * Z_EXAG,
                 color=it["color"], lw=2.0,
                 label=f"{it['h']:02d}:00  climb={it['climb_total']}")
    start_alt = (od[2] + 1.0) * dz
    goal_alt = (od[5] + 1.0) * dz
    ax0.scatter([od[0]], [od[1]], [start_alt * Z_EXAG], color="white",
                edgecolors="k", s=110, marker="o", zorder=5, label="start")
    ax0.scatter([od[3]], [od[4]], [goal_alt * Z_EXAG], color="yellow",
                edgecolors="k", s=200, marker="*", zorder=5, label="goal")
    ax0.set_xlabel("x (grid)")
    ax0.set_ylabel("y (grid)")
    ax0.set_zlabel(f"altitude (m, ×{Z_EXAG:.0f})")
    zticks = np.arange(0, 130, 30)
    ax0.set_zticks(zticks * Z_EXAG)
    ax0.set_zticklabels([f"{int(v)}" for v in zticks])
    ax0.set_title("(a) 3D view — planned paths vary in altitude")
    ax0.legend(fontsize=7, loc="upper left")

    # (b) 平面俯视 + 建筑底图
    ax1 = fig.add_subplot(gs[0, 1])
    b_vmax = float(np.percentile(building_heights, 98))
    if b_vmax <= 0:
        b_vmax = float(building_heights.max()) or 1.0
    ax1.imshow(building_heights.T, origin="lower", cmap="Greys",
               vmin=0, vmax=b_vmax, interpolation="nearest")
    for it in items:
        ax1.plot(it["xs"], it["ys"], color=it["color"], lw=2.0,
                 label=f"{it['h']:02d}:00")
    ax1.plot(od[0], od[1], "o", color="white", ms=10, mec="k", label="start")
    ax1.plot(od[3], od[4], "*", color="yellow", ms=15, mec="k", label="goal")
    ax1.set_title("(b) Plan view (x-y) with building heights")
    ax1.set_xlabel("x (grid)")
    ax1.set_ylabel("y (grid)")
    ax1.legend(loc="upper left", fontsize=8, framealpha=0.9)

    # (c) 高度剖面
    ax2 = fig.add_subplot(gs[0, 2])
    for it in items:
        ax2.plot(it["cum_h"], it["alts"], color=it["color"], lw=2.0,
                 label=f"{it['h']:02d}:00")
    ax2.axhline((od[2] + 1) * dz, ls="--", c="grey", lw=1,
                label=f"OD altitude {(od[2] + 1) * dz:.0f} m")
    ax2.set_title("(c) Altitude profile vs horizontal distance")
    ax2.set_xlabel("cumulative horizontal distance (m)")
    ax2.set_ylabel("altitude (m)")
    ax2.legend(fontsize=8, loc="upper right")

    fig.suptitle(
        "Figure 3b — 3D characterization of planned paths "
        f"(same OD, {len(items)} departure times; dz={dz:.0f} m, "
        f"altitude ×{Z_EXAG:.0f} for clarity)",
        fontsize=13,
    )
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
    print(f"[fig3b] saved {out_path}")

    # ---- 实证 z 统计表 ----
    stats_rows = []
    for it in items:
        stats_rows.append({
            "hour": f"{it['h']:02d}",
            "nodes": len(it["coords"]),
            "nz_unique": len(np.unique(it["zs"])),
            "z_min": int(it["zs"].min()),
            "z_max": int(it["zs"].max()),
            "alt_min_m": f"{it['alts'].min():.0f}",
            "alt_max_m": f"{it['alts'].max():.0f}",
            "climb_total": it["climb_total"],
            "L3d_m": f"{it['L3d']:.0f}",
            "Lh_m": f"{it['Lh']:.0f}",
        })
    if stats_path is not None:
        from exp_metrics import write_csv
        write_csv(stats_path, stats_rows)
        print(f"[fig3b] saved {stats_path}")

    print("[fig3b] 3D path statistics:")
    for r in stats_rows:
        print("  " + ", ".join(f"{k}={v}" for k, v in r.items()))
    return len(items), stats_rows
