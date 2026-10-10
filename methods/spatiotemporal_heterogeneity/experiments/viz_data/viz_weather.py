#!/usr/bin/env python3
"""
降水 / 风场「空间 — 时间 / 高度」异质性可视化（基于 scenario 环境模型）

论文情景化气象环境模型：

    降水  I(x,y,t) = I_ref(scenario) · S(x,y) · T(t)            [mm/h]
    风场  V(x,y,z,t) = V_ref(t) · F_z(z) · F_urban(x,y) · F_gust(t)  [m/s]

- 降水：纯 空间×时间 异质性（空间 hotspot + 时段窗 T(t)）
- 风场：空间（城市遮蔽 F_urban）× 时间（日变化 V_ref）× 高度（廓线 F_z）三维异质性

本脚本用情景模型类（ScenarioRainEnvironment / ScenarioWindEnvironment）在 **Exp1 的宏观
网格（100×100×12×96，dx≈48.46m、dy≈47.94m，96×15min）** 上重建张量，再从空间 / 时间 /
空间×时间（风场再加高度×时间）三个角度呈现其异质性，与 viz_noise.py 同口径。

数据口径与 Exp1（experiments/exp1_.../config.yaml）严格一致：
  - 网格：get_macro_grid()（真实案例尺度 100×100，与 data/02_processed 对齐）
  - 建筑高度：data/02_processed/building_heights.npy（100×100 真实），仅风场城市遮蔽
    F_urban 用（由 SVF 推导）；与 Exp1 run.py 调用 build_wind_tensor(..., building_heights=...)
    同源。
  - 风情景：moderate（V_ref=6 m/s），与 Exp1 params.wind_scenario 一致。
  - 降雨：情景模型与 Exp1 继承同一套 common.yaml 参数（中雨 8mm/h、14–20h、中心热点
    半径 20）；但 Exp1 默认 rain.enabled=false（f_rain≡1，不参与风险场）——本图仅为情景
    模型独立示意，已在标题注明。可用 --no-rain 仅绘制 Exp1 实际参与的纯风场。

重要：风/雨均为情景化合成（非实测、非 CFD，metadata.is_observed=False），图中已标注。

运行：python3 viz_weather.py [--save] [--no-rain] [--rain-scenario moderate]
                          [--wind-scenario moderate] [--altitude 50]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import PowerNorm, LinearSegmentedColormap
from matplotlib.ticker import FuncFormatter

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---- 路径引导（与 viz_noise.py / viz_population.py 一致）----
HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE.parent.parent                       # .../spatiotemporal_heterogeneity
PROC = MODULE_ROOT / "data" / "02_processed"          # 真实数据（顶层，与 Exp1 一致）
SRC = MODULE_ROOT / "src"


def _load_real_building_heights():
    """100×100 真实建筑高度（data/02_processed/building_heights.npy），供风场城市遮蔽
    F_urban 使用——与 Exp1 run.py 调用 build_wind_tensor(..., building_heights=...) 同源。"""
    p = PROC / "building_heights.npy"
    if p.exists():
        return np.load(p).astype(np.float32)
    raise FileNotFoundError(f"未找到真实建筑高度 {p}（Exp1 宏观网格用 100×100）")


def _build_inputs():
    """构造 Exp1 的宏观网格（100×100）+ 真实建筑高度，并导入情景环境模型类。"""
    import sys
    sys.path.insert(0, str(SRC))
    from tensor_engine.grid_system import get_macro_grid
    from tensor_engine.rain_environment import ScenarioRainEnvironment
    from tensor_engine.wind_environment import ScenarioWindEnvironment

    grid = get_macro_grid()                            # 100×100×12×96（真实案例尺度）
    building = _load_real_building_heights()           # (100, 100) 真实
    # 形状校验：与宏观网格严格对齐
    if tuple(building.shape) != (grid.spatial.nx, grid.spatial.ny):
        raise ValueError(
            f"真实建筑高度 {building.shape} 与宏观网格 "
            f"{(grid.spatial.nx, grid.spatial.ny)} 不符；请检查 data/02_processed 版本。"
        )
    return grid, building, ScenarioRainEnvironment, ScenarioWindEnvironment


# ============================================================================
# 降水场景可视化
# ============================================================================
def build_rain_figure(grid, RainEnv, rain_scenario: str = "moderate"):
    nt = grid.temporal.nt
    hours = grid.time_hours  # (nt,)
    nx, ny = grid.spatial.nx, grid.spatial.ny

    env = RainEnv(scenario_name=rain_scenario)
    rain = env.build_rain_tensor(grid)                 # (nx, ny, nt) mm/h
    meta = env.get_metadata()

    # 分量（用于拆解异质性）
    s_spatial = (rain.reshape(nx, ny, nt).max(axis=2)) / (meta["intensity_mmh"] + 1e-12)  # S(x,y)∈[0,1]
    # 时间包络 T(t)：用首个空间单元还原（S 已归一，T=rain/(I_ref*S)）
    with np.errstate(divide="ignore", invalid="ignore"):
        t_env = np.nanmax(rain / (meta["intensity_mmh"] * (s_spatial[..., None] + 1e-12)), axis=(0, 1))
    t_env = np.nan_to_num(t_env, nan=0.0)

    # 峰值 / 谷值时刻
    peak_t = int(np.argmax(t_env))
    # 谷值：取 T(t) 最小的“时段外”时刻（若全为非零，则取最小）
    off_t = int(np.argmin(t_env))
    day_t = int(np.argmin(np.abs(hours - 14.0)))

    # 共享颜色上限（峰值 + 谷值合起来 99.5 分位，保证可比）；数据偏斜用 PowerNorm
    vmax = float(np.percentile(rain.reshape(-1), 99.5))
    shared_norm = PowerNorm(gamma=0.4, vmin=0, vmax=vmax)

    # 空间×时间热力图：沿 y 取均值 -> (x, t)，展示“何处、何时”有雨
    spatial_t_hm = rain.mean(axis=1)                   # (x, t)

    # 代表性单元：hotspot 中心、半径边缘、开敞角
    cx, cy = (nx / 2.0, ny / 2.0)
    ih, jh = int(round(cx)), int(round(cy))
    # 背景：取 S 最小处
    bg_idx = np.unravel_index(np.argmin(s_spatial), s_spatial.shape)
    ib, jb = int(bg_idx[0]), int(bg_idx[1])

    fig = plt.figure(figsize=(19, 11))
    fig.suptitle(
        f"降水情景 I(x,y,t) = I_ref·S(x,y)·T(t)  ［情景模型示意］\n"
        f"情景={rain_scenario}（I_ref={meta['intensity_mmh']} mm/h），真实案例尺度 {nx}×{ny}×{nt}"
        f"（Exp1 宏观网格 100×100）\n"
        f"—— 空间异质性（hotspot）｜ 时间异质性（时段窗 {meta['active_hours']}h）｜ 空间×时间联合\n"
        f"注：Exp1 默认 rain.enabled=false（f_rain≡1，不参与风险场）；此图仅为情景模型独立说明",
        fontsize=12, fontweight="bold",
    )

    # (0,0) S(x,y) 空间 hotspot
    ax0 = fig.add_subplot(2, 3, 1)
    im0 = ax0.imshow(s_spatial.T, origin="lower", cmap="YlOrBr", interpolation="nearest",
                     vmin=0, vmax=1)
    ax0.set_title("① 空间分布 S(x,y)\n（hotspot：高斯衰减，半径≈%.0f 格）" % meta["radius_grids"])
    ax0.set_xlabel("X（网格）"); ax0.set_ylabel("Y（网格）")
    fig.colorbar(im0, ax=ax0, fraction=0.046, label="S(x,y)∈[0,1]")
    # 标出 hotspot 中心
    ax0.plot([ih], [jh], "r*", ms=10, label="hotspot 中心"); ax0.legend(fontsize=7, loc="upper right")

    # (0,1) 峰值时刻空间分布
    ax1 = fig.add_subplot(2, 3, 2)
    im1 = ax1.imshow(rain[:, :, peak_t].T, origin="lower", cmap="Blues",
                     interpolation="nearest", norm=shared_norm)
    ax1.set_title(f"② 峰值时刻降水空间分布 (t={peak_t}→{hours[peak_t]:.1f}h)")
    ax1.set_xlabel("X（网格）"); ax1.set_ylabel("Y（网格）")
    fig.colorbar(im1, ax=ax1, fraction=0.046, label="降水强度 mm/h")

    # (0,2) 谷值/时段外时刻空间分布（应接近 0，体现时间门控）
    ax2 = fig.add_subplot(2, 3, 3)
    im2 = ax2.imshow(rain[:, :, off_t].T, origin="lower", cmap="Blues",
                     interpolation="nearest", norm=shared_norm)
    ax2.set_title(f"③ 时段外降水空间分布 (t={off_t}→{hours[off_t]:.1f}h)\n"
                  f"（T(t) 门控：此时段外强度≈0）")
    ax2.set_xlabel("X（网格）"); ax2.set_ylabel("Y（网格）")
    fig.colorbar(im2, ax=ax2, fraction=0.046, label="降水强度 mm/h")

    # (1,0) T(t) 时间包络
    ax3 = fig.add_subplot(2, 3, 4)
    ax3.plot(np.arange(nt) * 0.25, t_env, color="navy", lw=2, label="T(t) 时间包络")
    h0, h1 = float(meta["active_hours"][0]), float(meta["active_hours"][1])
    ax3.axvspan(h0, h1, color="royalblue", alpha=0.12, label=f"活跃时段 {h0:.0f}–{h1:.0f}h")
    ax3.set_title("④ 时间包络 T(t)\n（矩形窗 + 边缘平滑 σ=%.2f）" % meta["edge_softness"])
    ax3.set_xlabel("小时 (h)"); ax3.set_ylabel("T(t)∈[0,1]")
    ax3.set_xlim(0, 24); ax3.grid(alpha=0.3); ax3.legend(fontsize=8)

    # (1,1) 全天时序：hotspot 中心 vs 背景
    ax4 = fig.add_subplot(2, 3, 5)
    rain_h = rain.reshape(nx * ny, nt)
    series_hot = rain[ih, jh, :]
    series_bg = rain[ib, jb, :]
    ax4.plot(np.arange(nt) * 0.25, series_hot, color="#d73027", lw=1.8, label="hotspot 中心")
    ax4.plot(np.arange(nt) * 0.25, series_bg, color="#4575b4", lw=1.8, label="开敞背景")
    ax4.plot(np.arange(nt) * 0.25, rain_h.mean(axis=0), color="black", lw=1.2, ls="--", label="空间均值")
    ax4.set_title("⑤ 全天降水强度时序\n（时间异质性：时段窗内骤升骤降）")
    ax4.set_xlabel("小时 (h)"); ax4.set_ylabel("降水强度 mm/h")
    ax4.set_xlim(0, 24); ax4.grid(alpha=0.3); ax4.legend(fontsize=8)

    # (1,2) 空间×时间热力图 (x × hour)
    ax5 = fig.add_subplot(2, 3, 6)
    hm = spatial_t_hm  # (x, t)
    im5 = ax5.imshow(hm, aspect="auto", cmap="Blues", origin="lower",
                     extent=[0, 24, 0, nx], interpolation="nearest")
    ax5.set_title("⑥ 空间×时间联合：降水强度沿 X(行) × 小时(列)\n"
                  "（何处、何时降水最强）")
    ax5.set_xlabel("小时 (h)"); ax5.set_ylabel("X 网格行")
    ax5.set_xlim(0, 24)
    fig.colorbar(im5, ax=ax5, fraction=0.046, label="mm/h")
    # 标注峰值行
    peak_row = int(np.argmax(hm.mean(axis=1)))
    ax5.axhline(peak_row, color="red", lw=0.8, ls=":")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig, dict(rain=rain, meta=meta, peak_t=peak_t, off_t=off_t,
                     vmax=vmax, s_spatial=s_spatial, t_env=t_env)


# ============================================================================
# 风场场景可视化
# ============================================================================
def build_wind_figure(grid, WindEnv, building, wind_scenario: str = "moderate",
                      altitude_m: float = 50.0):
    nt = grid.temporal.nt
    hours = grid.time_hours
    nx, ny, nz = grid.spatial.nx, grid.spatial.ny, grid.spatial.nz
    z_heights = grid.z_heights.astype(np.float64)

    env = WindEnv(scenario_name=wind_scenario)
    wind = env.build_wind_tensor(grid=grid, building_heights=building)   # (nx,ny,nz,nt) m/s
    meta = env.get_metadata()

    z_idx = int(np.argmin(np.abs(z_heights - altitude_m)))
    z_val = float(z_heights[z_idx])
    wind_z = wind[:, :, z_idx, :]                              # (nx,ny,nt) @ z

    # 分量拆解
    # F_urban(x,y)：风速被城市遮蔽衰减 -> 由 wind 在某恒定 t/z 归一得到
    ref_t = int(np.argmin(np.abs(hours - 12.0)))
    base = meta["reference_speed"] * env._temporal_factor(hours)[ref_t] * env._vertical_factor(z_heights)[z_idx]
    f_urban = np.clip(wind[:, :, z_idx, ref_t] / (base + 1e-12), 0, 1)   # (nx,ny)
    f_z = env._vertical_factor(z_heights)                      # (nz,)
    v_ref = env._temporal_factor(hours) * meta["reference_speed"]          # (nt,)

    # 风场热点/开敞代表点：F_urban 最小（开敞）与最大（深峡谷）
    open_idx = np.unravel_index(np.argmin(f_urban), f_urban.shape)
    canyon_idx = np.unravel_index(np.argmax(f_urban), f_urban.shape)
    io, jo = int(open_idx[0]), int(open_idx[1])
    ic, jc = int(canyon_idx[0]), int(canyon_idx[1])

    # 共享颜色上限（参考高度全时相 99.5 分位）
    # 注：风速分布近均匀（非偏斜），用线性色标才能呈现峡谷/开敞的空间对比
    vmax = float(np.percentile(wind_z.ravel(), 99.5))
    vmin = float(np.percentile(wind_z.ravel(), 0.5))

    # 高度×时间热力图（去掉 F_urban，展示 V_ref(t)·F_z(z) 形状）：(z, hour)
    hour_edges = np.arange(0, nt + 1, 4)                       # 96->24
    zt = (v_ref[None, :] * f_z[:, None])                       # (nz, nt)
    zt_h = np.array([zt[:, h0:h1].mean(axis=1) for h0, h1 in zip(hour_edges[:-1], hour_edges[1:])]).T  # (nz,24)

    fig = plt.figure(figsize=(19, 11))
    fig.suptitle(
        f"风场情景 V(x,y,z,t) = V_ref(t)·F_z(z)·F_urban(x,y)·F_gust(t)  ［Exp1 实际参与项］\n"
        f"情景={wind_scenario}（V_ref={meta['reference_speed']} m/s）｜ 真实案例尺度 {nx}×{ny}×{nz}×{nt}"
        f"（Exp1 宏观网格 100×100，建筑遮蔽用真实 100×100 建筑高度）\n"
        f"—— 空间（城市遮蔽）｜ 时间（日变化）｜ 高度×时间联合  ［情景合成，is_observed=False］",
        fontsize=12, fontweight="bold",
    )

    # (0,0) F_urban 城市遮蔽空间分布（静态）
    ax0 = fig.add_subplot(2, 3, 1)
    im0 = ax0.imshow(f_urban.T, origin="lower", cmap="RdYlGn", interpolation="nearest",
                     vmin=float(f_urban.min()), vmax=1.0)
    ax0.set_title("① 城市遮蔽 F_urban(x,y)\n（深峡谷遮蔽衰减↓，开敞≈1；红=衰减强）")
    ax0.set_xlabel("X（网格）"); ax0.set_ylabel("Y（网格）")
    fig.colorbar(im0, ax=ax0, fraction=0.046, label="F_urban∈[%.2f,1]" % f_urban.min())
    ax0.plot([io], [jo], "b^", ms=9, label="最开敞"); ax0.plot([ic], [jc], "rv", ms=9, label="最深峡谷")
    ax0.legend(fontsize=7, loc="upper right", framealpha=0.9)

    # (0,1) 参考高度 + 峰值时刻空间分布
    peak_t = int(np.argmax(v_ref))
    ax1 = fig.add_subplot(2, 3, 2)
    im1 = ax1.imshow(wind_z[:, :, peak_t].T, origin="lower", cmap="coolwarm",
                     interpolation="nearest", vmin=vmin, vmax=vmax)
    ax1.set_title(f"② 峰值时刻风速空间分布 (z={z_val:.0f}m, t={peak_t}→{hours[peak_t]:.1f}h)")
    ax1.set_xlabel("X（网格）"); ax1.set_ylabel("Y（网格）")
    fig.colorbar(im1, ax=ax1, fraction=0.046, label="风速 m/s")

    # (0,2) 参考高度 + 谷值时刻空间分布
    off_t = int(np.argmin(v_ref))
    ax2 = fig.add_subplot(2, 3, 3)
    im2 = ax2.imshow(wind_z[:, :, off_t].T, origin="lower", cmap="coolwarm",
                     interpolation="nearest", vmin=vmin, vmax=vmax)
    ax2.set_title(f"③ 谷值时刻风速空间分布 (z={z_val:.0f}m, t={off_t}→{hours[off_t]:.1f}h)\n"
                  f"（日变化 V_ref 调制整体量级）")
    ax2.set_xlabel("X（网格）"); ax2.set_ylabel("Y（网格）")
    fig.colorbar(im2, ax=ax2, fraction=0.046, label="风速 m/s")

    # (1,0) F_z(z) 高度廓线
    ax3 = fig.add_subplot(2, 3, 4)
    ax3.plot(z_heights, f_z, color="darkgreen", lw=2.2, marker="o", ms=4, label="F_z(z)")
    ax3.axhline(1.0, color="grey", ls="--", lw=1, label="参考层 (=1)")
    ax3.set_title("④ 高度修正 F_z(z)\n（风险导向垂直修正：低空遮蔽、高空增益）")
    ax3.set_xlabel("高度 (m)"); ax3.set_ylabel("F_z(z)")
    ax3.grid(alpha=0.3); ax3.legend(fontsize=8)

    # (1,1) 全天时序：开敞 vs 深峡谷（两条线，体现地点依赖）
    ax4 = fig.add_subplot(2, 3, 5)
    ax4.plot(np.arange(nt) * 0.25, wind_z[io, jo, :], color="#1a9850", lw=1.8, label="最开敞点")
    ax4.plot(np.arange(nt) * 0.25, wind_z[ic, jc, :], color="#d73027", lw=1.8, label="最深峡谷点")
    ax4.plot(np.arange(nt) * 0.25, wind_z.reshape(-1, nt).mean(axis=0), color="black",
             lw=1.2, ls="--", label="空间均值")
    ax4.set_title("⑤ 全天风速时序（地点依赖）\n"
                  "（时间异质性：V_ref 日变化；峡谷点整体偏低=F_urban 衰减）")
    ax4.set_xlabel("小时 (h)"); ax4.set_ylabel("风速 m/s")
    ax4.set_xlim(0, 24); ax4.grid(alpha=0.3); ax4.legend(fontsize=8)

    # (1,2) 高度×时间热力图 (z × hour)
    ax5 = fig.add_subplot(2, 3, 6)
    im5 = ax5.imshow(zt_h, aspect="auto", cmap="coolwarm", origin="lower",
                     extent=[0, 24, 0, nz - 1])
    ax5.set_title("⑥ 高度×时间联合：V_ref(t)·F_z(z)\n（行=垂直层 0..%d，列=小时）" % (nz - 1))
    ax5.set_xlabel("小时 (h)"); ax5.set_ylabel("垂直层 (0=低空, %d=高空)" % (nz - 1))
    ax5.set_xlim(0, 24)
    cbi = fig.colorbar(im5, ax=ax5, fraction=0.046, label="风速 m/s")
    # 标注参考高度层
    ax5.axhline(z_idx, color="black", lw=1.0, ls=":")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig, dict(wind=wind, meta=meta, z_idx=z_idx, z_val=z_val, vmax=vmax,
                     f_urban=f_urban, f_z=f_z, v_ref=v_ref,
                     open_idx=(io, jo), canyon_idx=(ic, jc))


def _print_summary(grid, r_rain, r_wind):
    nx, ny, nz, nt = grid.shape
    print("=" * 64)
    print("降水 / 风场 情景空间-时间异质性摘要（对应 Exp1 宏观网格 100×100）")
    print("=" * 64)
    wm = r_wind["meta"]
    print(f"网格: {nx}×{ny}×{nz}×{nt}（get_macro_grid，真实案例尺度）"
          f"  参考高度 z={r_wind['z_val']:.0f} m (层 {r_wind['z_idx']})")
    if r_rain is not None:
        rm = r_rain["meta"]
        print(f"[降水·情景示意] 情景={rm['scenario']} I_ref={rm['intensity_mmh']} mm/h "
              f"时段={rm['active_hours']}h  峰值时刻 t={r_rain['peak_t']}")
        print(f"       降水 @峰值: 范围[{r_rain['rain'][:,:,r_rain['peak_t']].min():.3f}, "
              f"{r_rain['rain'][:,:,r_rain['peak_t']].max():.3f}] mm/h")
        print(f"       注：Exp1 默认 rain.enabled=false（f_rain≡1），此为独立情景示意。")
    else:
        print("[降水] 跳过（--no-rain：Exp1 实际不参与降雨）")
    print(f"[风场·Exp1 实际项] 情景={wm['scenario']} V_ref={wm['reference_speed']} m/s  "
          f"F_urban∈[{r_wind['f_urban'].min():.2f},{r_wind['f_urban'].max():.2f}]")
    print(f"       风速 @z={r_wind['z_val']:.0f}m: 范围[{r_wind['wind'][:,:,r_wind['z_idx'],:].min():.3f}, "
          f"{r_wind['wind'][:,:,r_wind['z_idx'],:].max():.3f}] m/s")
    print(f"       注意：风场为情景化合成（is_observed={wm.get('is_observed')}），非实测/非 CFD；"
          f"城市遮蔽由真实 100×100 建筑高度（SVF）推导，与 Exp1 run.py 同源。")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser(description="降水/风场情景空间-时间异质性可视化（对应 Exp1 输入口径）")
    ap.add_argument("--save", action="store_true", help="保存到 output/统计/ 而非仅弹窗")
    ap.add_argument("--no-rain", action="store_true",
                    help="仅绘制 Exp1 实际参与的纯风场（跳过降雨示意；Exp1 默认关闭降雨）")
    ap.add_argument("--rain-scenario", default="moderate", help="降水情景 light/moderate/heavy")
    ap.add_argument("--wind-scenario", default="moderate", help="风情景 weak/moderate/strong")
    ap.add_argument("--altitude", type=float, default=50.0, help="风场参考飞行高度 (m)")
    args = ap.parse_args()

    grid, building, RainEnv, WindEnv = _build_inputs()

    fig_wind, r_wind = build_wind_figure(grid, WindEnv, building,
                                         wind_scenario=args.wind_scenario, altitude_m=args.altitude)
    if args.no_rain:
        r_rain = None
        fig_rain = None
        print("[rain] 跳过（--no-rain：Exp1 默认 rain.enabled=false）")
    else:
        fig_rain, r_rain = build_rain_figure(grid, RainEnv, rain_scenario=args.rain_scenario)
    _print_summary(grid, r_rain, r_wind)

    if args.save:
        out = MODULE_ROOT / "output" / "统计"
        out.mkdir(parents=True, exist_ok=True)
        p2 = out / "viz_wind_spatiotemporal.png"
        fig_wind.savefig(p2, dpi=130, bbox_inches="tight")
        print(f"已保存: {p2}")
        if fig_rain is not None:
            p1 = out / "viz_rain_spatiotemporal.png"
            fig_rain.savefig(p1, dpi=130, bbox_inches="tight")
            print(f"已保存: {p1}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
