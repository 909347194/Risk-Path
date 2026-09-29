#!/usr/bin/env python3
"""Figure 5：时空异质性存在性证明（连续演化视角）。

四个面板：
  (a) 走廊—时间风险热图：OD 沿线 P_crash 随 96 时相连续演化（"演化"观感）
  (b) 热点昼夜曲线：人口核心 A/B 与全域均值的 P_crash(t)，展示相位交替
  (c) ΔP_crash(12:00 − 22:00) 差值图：风险的空间重分布
  (d) 垂直异质性：全城均值 P_crash 随高度变化（4 个出发时刻）

返回附加指标行（可并入 heterogeneity.csv）。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

# 真实人口潮汐双核心（README / exp_metrics 核验位置）
CORE_A = (22, 52)   # 昼间峰值
CORE_B = (72, 18)   # 夜间峰值


def plot_fig5(grid, p_crash, od, results, hours, z_layer, out_path):
    nx, ny, nz, nt = grid.shape
    dx, dy = grid.spatial.dx, grid.spatial.dy
    t_hours = np.arange(nt) * (grid.temporal.dt_minutes / 60.0)

    # ---------- (a) 走廊—时间热图 ----------
    sx, sy, gx, gy = od[0], od[1], od[3], od[4]
    n_sample = 120
    xs = np.linspace(sx, gx, n_sample)
    ys = np.linspace(sy, gy, n_sample)
    ii = np.clip(xs.astype(int), 0, nx - 1)
    jj = np.clip(ys.astype(int), 0, ny - 1)
    profile = p_crash[ii, jj, z_layer, :]                     # (n_sample, nt)
    dist = np.linspace(0, np.hypot((gx - sx) * dx, (gy - sy) * dy), n_sample)

    # ---------- (b) 热点昼夜曲线 ----------
    ax_i, ay_i = CORE_A
    bx_i, by_i = CORE_B
    curve_a = p_crash[ax_i, ay_i, z_layer, :]
    curve_b = p_crash[bx_i, by_i, z_layer, :]
    curve_mean = p_crash[:, :, z_layer, :].mean(axis=(0, 1))

    # ---------- (c) ΔP_crash(12h − 22h) ----------
    t12, t22 = grid.get_time_index(12), grid.get_time_index(22)
    delta = p_crash[:, :, z_layer, t12] - p_crash[:, :, z_layer, t22]

    # ---------- (d) 垂直廓线 ----------
    z_heights = grid.z_heights
    z_curves = {}
    for h in hours:
        t_idx = grid.get_time_index(h)
        z_curves[h] = p_crash[:, :, :, t_idx].mean(axis=(0, 1))

    # ================= 绘图 =================
    fig, axes = plt.subplots(2, 2, figsize=(14, 9.5), layout="constrained")
    fig.suptitle(
        "Figure 5 — Spatiotemporal heterogeneity of the risk field: existence proof\n"
        "continuous temporal evolution along the corridor | hotspot phase alternation | "
        "spatial redistribution | vertical profile",
        fontsize=12.5,
    )

    # (a)
    ax = axes[0, 0]
    vmax_p = float(np.percentile(profile, 99))
    im0 = ax.imshow(
        profile.T, origin="lower", aspect="auto", cmap="inferno",
        extent=[0, dist[-1], t_hours[0], t_hours[-1]], vmin=0, vmax=max(vmax_p, 1e-9),
    )
    for h in hours:
        ax.axhline(h, color="cyan", lw=0.8, ls="--", alpha=0.7)
    ax.set_xlabel("distance along OD corridor (m)")
    ax.set_ylabel("hour of day")
    ax.set_title("(a) $P_{crash}$ along corridor vs time (z≈60 m)")
    fig.colorbar(im0, ax=ax, shrink=0.9)

    # (b)
    ax = axes[0, 1]
    ax.plot(t_hours, curve_a, label=f"core A {CORE_A} (day-peak)", lw=1.8)
    ax.plot(t_hours, curve_b, label=f"core B {CORE_B} (night-peak)", lw=1.8)
    ax.plot(t_hours, curve_mean, label="city mean", lw=1.4, ls="--", color="gray")
    for h in hours:
        ax.axvline(h, color="k", lw=0.7, ls=":", alpha=0.6)
    ax.set_xlabel("hour of day")
    ax.set_ylabel("$P_{crash}$")
    ax.set_title("(b) hotspot diurnal profiles (phase alternation)")
    ax.legend(fontsize=9)

    # (c)
    ax = axes[1, 0]
    v = float(np.percentile(np.abs(delta), 98)) or 1e-9
    im2 = ax.imshow(
        delta.T, origin="lower", cmap="RdBu_r",
        norm=TwoSlopeNorm(vmin=-v, vcenter=0.0, vmax=v),
    )
    ax.plot(xs, ys, color="k", lw=1.2, ls="--", label="OD corridor")
    ax.plot(sx, sy, "o", color="lime", ms=8, label="start")
    ax.plot(gx, gy, "*", color="red", ms=12, label="goal")
    ax.set_title("(c) $\\Delta P_{crash}$ = 12:00 − 22:00 (red = riskier at noon)")
    ax.legend(fontsize=8, loc="upper right")
    fig.colorbar(im2, ax=ax, shrink=0.9)

    # (d)
    ax = axes[1, 1]
    for h in hours:
        ax.plot(z_heights, z_curves[h], marker="o", ms=3.5, lw=1.6, label=f"{h:02d}:00")
    ax.set_xlabel("altitude z (m)")
    ax.set_ylabel("city-mean $P_{crash}$")
    ax.set_title("(d) vertical risk profile at 4 departure hours")
    ax.legend(fontsize=9)

    fig.savefig(out_path, dpi=140)
    plt.close(fig)

    # ================= 附加指标行 =================
    def _peak_hour(curve):
        return float(t_hours[int(np.argmax(curve))])

    corridor_mean_t = profile.mean(axis=0)
    peak_t = _peak_hour(corridor_mean_t)
    trough_t = float(t_hours[int(np.argmin(corridor_mean_t))])
    ratio = float(corridor_mean_t.max() / max(corridor_mean_t.min(), 1e-12))
    rows = [
        {"metric": "corridor_risk_peak_hour", "value": peak_t},
        {"metric": "corridor_risk_trough_hour", "value": trough_t},
        {"metric": "corridor_risk_peak_trough_ratio", "value": round(ratio, 3)},
        {"metric": "core_A_peak_hour", "value": _peak_hour(curve_a)},
        {"metric": "core_B_peak_hour", "value": _peak_hour(curve_b)},
        {"metric": "delta_12h_22h_mean_abs", "value": round(float(np.mean(np.abs(delta))), 6)},
        {"metric": "delta_12h_22h_p98", "value": round(float(v), 6)},
        {"metric": "z_profile_spread_ratio", "value": round(
            float(max(z.max() for z in z_curves.values())
                  / max(min(z.min() for z in z_curves.values()), 1e-12)), 3)},
    ]
    return rows
