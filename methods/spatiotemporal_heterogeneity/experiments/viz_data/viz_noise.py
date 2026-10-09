#!/usr/bin/env python3
"""
噪声成本「空间 — 时间」异质性可视化（基于 dynamic_noise 模型）

论文滋扰成本模型：

    Cost_noise(i, z, t) = I_noise(z) · ρ_pop(i, t) · S_landuse(i) · T_penalty(i, t)

- 空间维度驱动：S_landuse(i)（用地敏感度）+ ρ_pop(i, t) 的空间分布
- 时间维度驱动：T_penalty(i, t)（昼夜惩罚）+ ρ_pop(i, t) 的时变潮汐

本脚本用真实数据（landuse_map.npy + rho_pop_3d.npy）在真实网格
(100×100×12×96) 上算一遍 4D 噪声成本张量，再从三个角度呈现其
在空间 / 时间上的变化：

  1) 静态空间敏感度 S_landuse 地图        —— 纯空间驱动（用地类型）
  2) 昼 / 夜 噪声成本空间地图             —— 空间分布随时间的切换
  3) 全天（96 时相）空间均值曲线          —— 整体时间变化
  4) 分用地类型的全天曲线                 —— 时间变化如何因地点而异
  5) 用地类型 × 小时 的 S-T 热力图        —— 空间 × 时间的联合变化

只弹窗显示，不落盘（加 --save 才写 output/统计/）。
数组轴序 [ix, iy]，显示需转置 + origin="lower"。

运行：python3 viz_noise.py [--save]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, PowerNorm

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

# ---- 路径引导（与 viz_population.py 一致）----
HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE.parent.parent                       # .../spatiotemporal_heterogeneity
PROC = MODULE_ROOT / "data" / "02_processed"
SRC = MODULE_ROOT / "src"

# 真实广州中心区范围（与 viz_population 共用，保证空间坐标一致）
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]

# ---- 6 类用地的显示名 + 颜色（与 NoiseConfig.landuse_code_map 对应）----
CLASS_ORDER = [
    ("natural_open",            "自然/开阔",   "#a6d96a"),
    ("residential",             "居住区",     "#fdae61"),
    ("commercial_administrative","商业/行政",  "#ffd24d"),
    ("quiet_service",           "宁静服务",   "#d73027"),
    ("industrial_logistics",    "工业/物流",  "#bdbdbd"),
    ("infrastructure_transport","交通走廊",   "#762a83"),
]
CLASS_NAMES = [c[0] for c in CLASS_ORDER]
CLASS_LABELS = [c[1] for c in CLASS_ORDER]
CLASS_COLORS = [c[2] for c in CLASS_ORDER]


def _load_inputs():
    """读取真实 landuse 与动态人口，并构造匹配网格。"""
    import sys
    sys.path.insert(0, str(SRC))
    from tensor_engine.dynamic_noise import DynamicNoiseCost
    from tensor_engine.grid_system import GridSystem, SpatialGridConfig, TemporalGridConfig

    landuse = np.load(PROC / "landuse_map.npy").astype(np.int32)   # (100, 100)
    rho_pop = np.load(PROC / "rho_pop_3d.npy").astype(np.float64)  # (100, 100, 96)

    nx, ny = landuse.shape
    nt = rho_pop.shape[-1]
    nz = 12
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=nx, ny=ny, nz=nz),
        temporal=TemporalGridConfig(nt=nt, dt_minutes=15),
    )
    model = DynamicNoiseCost(grid=grid)
    return model, grid, landuse, rho_pop


def _z_index_for_altitude(grid, altitude_m: float) -> int:
    z = grid.z_heights
    return int(np.argmin(np.abs(z - altitude_m)))


def _class_mask(canonical, name):
    return canonical == name


def build_figure(model, grid, landuse, rho_pop, altitude_m: float = 50.0):
    """构建 2×3 综合图：上排空间，下排时间 / 空间×时间。"""
    nx, ny, nz, nt = grid.shape
    z_idx = _z_index_for_altitude(grid, altitude_m)
    z_val = float(grid.z_heights[z_idx])

    # ---- 1. 计算 4D 噪声成本张量 ----
    noise = model.compute_noise_cost(landuse=landuse, population_density=rho_pop)  # (nx,ny,nz,nt)
    cost_z = noise[:, :, z_idx, :]                                                # (nx,ny,nt) @ z=alt

    # ---- 分量的空间/时间结构（用于解释驱动）----
    s_landuse = model.compute_landuse_sensitivity(landuse)                        # (nx,ny)
    canonical = model.canonicalize_landuse(landuse)                               # (nx,ny) 类名

    # ---- 昼 / 夜 时相索引 ----
    hours = grid.time_hours
    day_t = int(np.argmin(np.abs(hours - 13.0)))     # 13:00 昼间
    night_t = int(np.argmin(np.abs(hours - 23.0)))   # 23:00 夜间

    # 共享颜色上限（白天+夜间合起来取 99.5 分位），保证两图可比；
    # 数据高度偏斜（少数热点 >> 主体），用 PowerNorm 抬升低值结构
    vmax = float(np.percentile(np.concatenate([cost_z[:, :, day_t].ravel(),
                                               cost_z[:, :, night_t].ravel()]), 99.5))
    shared_norm = PowerNorm(gamma=0.4, vmin=0, vmax=vmax)

    # ---- 分用地类型全天均值（用于时间曲线 & S-T 热力图）----
    hour_edges = np.arange(0, nt + 1, 4)            # 96 → 24 小时
    class_t_mean = {}                               # name -> (nt,)
    class_h_mean = {}                               # name -> (24,)
    for name in CLASS_NAMES:
        m = _class_mask(canonical, name)
        if not np.any(m):
            class_t_mean[name] = np.zeros(nt)
            class_h_mean[name] = np.zeros(len(hour_edges) - 1)
            continue
        tmean = cost_z[m].mean(axis=0)              # (nt,)
        hmean = np.array([cost_z[m][:, h0:h1].mean()
                          for h0, h1 in zip(hour_edges[:-1], hour_edges[1:])])
        class_t_mean[name] = tmean
        class_h_mean[name] = hmean

    # 整体空间均值曲线
    overall_t = cost_z.reshape(-1, nt).mean(axis=0)
    overall_h = np.array([overall_t[h0:h1].mean()
                          for h0, h1 in zip(hour_edges[:-1], hour_edges[1:])])

    # ================= 绘图 =================
    fig = plt.figure(figsize=(19, 11))
    fig.suptitle(
        f"噪声成本 Cost_noise(i,z,t) = I_noise(z)·ρ_pop(i,t)·S_landuse(i)·T_penalty(i,t)\n"
        f"真实数据网格 {nx}×{ny}×{nz}×{nt}，参考飞行高度 z={z_val:.0f} m（第 {z_idx} 层）\n"
        f"—— 左：空间异质性；右：时间异质性 / 空间×时间联合异质性",
        fontsize=13, fontweight="bold",
    )

    # ---------- 上排：空间 ---------- #
    # (0,0) 静态空间敏感度 S_landuse
    ax0 = fig.add_subplot(2, 3, 1)
    rgb = np.zeros((ny, nx, 3))
    for name, _lab, col in zip(CLASS_NAMES, CLASS_LABELS, CLASS_COLORS):
        m = _class_mask(canonical, name)            # (nx,ny)
        c = np.array(matplotlib.colors.to_rgb(col))
        rgb[m.T] = c                                # 显示需转置
    ax0.imshow(rgb, origin="lower", extent=EXTENT, interpolation="nearest")
    ax0.set_title("① 静态空间敏感度 S_landuse(i)\n（纯空间驱动：用地类型）")
    # 图例
    from matplotlib.patches import Patch
    ax0.legend(handles=[Patch(facecolor=col, label=lab) for col, lab in zip(CLASS_COLORS, CLASS_LABELS)],
               loc="upper right", fontsize=7, framealpha=0.85)

    # (0,1) 昼间噪声空间地图
    ax1 = fig.add_subplot(2, 3, 2)
    im1 = ax1.imshow(cost_z[:, :, day_t].T, origin="lower", extent=EXTENT,
                     cmap="magma", interpolation="nearest", norm=shared_norm)
    ax1.set_title(f"② 昼间噪声成本空间分布 (t={day_t}→{hours[day_t]:.1f}h)")
    fig.colorbar(im1, ax=ax1, fraction=0.046, label="噪声成本（非线性色标）")

    # (0,2) 夜间噪声空间地图
    ax2 = fig.add_subplot(2, 3, 3)
    im2 = ax2.imshow(cost_z[:, :, night_t].T, origin="lower", extent=EXTENT,
                     cmap="magma", interpolation="nearest", norm=shared_norm)
    ax2.set_title(f"③ 夜间噪声成本空间分布 (t={night_t}→{hours[night_t]:.1f}h)\n"
                  f"（居住区 T:昼1.5→夜10，夜间显著抬升）")
    fig.colorbar(im2, ax=ax2, fraction=0.046, label="噪声成本（非线性色标）")

    # ---------- 下排：时间 / 空间×时间 ---------- #
    # (1,0) 全天空间均值曲线（整体时间变化）+ 人口潮汐参考线
    ax3 = fig.add_subplot(2, 3, 4)
    ax3.plot(np.arange(nt) * 0.25, overall_t, color="black", lw=2, label="噪声成本空间均值")
    # 人口潮汐（小时均值后归一，画在右轴，展示第二种时间驱动）
    pop_tide = rho_pop.reshape(-1, nt).mean(axis=0)
    pop_h = np.array([pop_tide[h0:h1].mean()
                      for h0, h1 in zip(hour_edges[:-1], hour_edges[1:])])
    pop_h = pop_h / (pop_h.max() + 1e-12)
    ax3b = ax3.twinx()
    ax3b.plot(hour_edges[:-1] + 0.5, pop_h, color="steelblue", lw=1.4, ls="--",
              label="ρ_pop 空间均值（归一，右轴）")
    ax3b.set_ylabel("ρ_pop 相对值", color="steelblue", fontsize=9)
    ax3b.tick_params(axis="y", labelcolor="steelblue", labelsize=8)
    # 昼夜背景带
    ax3.axvspan(grid.time_hours[0], 7, color="navy", alpha=0.06)
    ax3.axvspan(20, 24, color="navy", alpha=0.06)
    ax3.axvspan(7, 20, color="orange", alpha=0.05)
    ax3.set_title("④ 全天噪声成本空间均值\n（时间变化：T_penalty 昼夜阶跃 + 人口潮汐）")
    ax3.set_xlabel("小时 (h)")
    ax3.set_ylabel("噪声成本（空间均值）")
    ax3.set_xlim(0, 24)
    ax3.grid(alpha=0.3)
    h1, l1 = ax3.get_legend_handles_labels()
    h2, l2 = ax3b.get_legend_handles_labels()
    ax3.legend(h1 + h2, l1 + l2, fontsize=8, loc="lower left")

    # (1,1) 分用地类型全天曲线（地点依赖的时间变化）
    #   自然/开阔 S=0 恒为零，对数轴下无法显示，剔除（其不敏感性见①）
    ax4 = fig.add_subplot(2, 3, 5)
    for name, lab, col in zip(CLASS_NAMES, CLASS_LABELS, CLASS_COLORS):
        if name == "natural_open":
            continue
        ax4.plot(np.arange(nt) * 0.25, np.maximum(class_t_mean[name], 1e-6),
                 color=col, lw=1.8, label=lab)
    ax4.set_yscale("log")
    # 中文字体缺 U+2212（数学负号）字形，改用 ASCII 刻度标签
    from matplotlib.ticker import FuncFormatter
    ax4.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax4.set_title("⑤ 分用地类型全天曲线（对数轴）\n（时间变化如何因地点/用地而异）")
    ax4.set_xlabel("小时 (h)")
    ax4.set_ylabel("噪声成本（该类空间均值，log）")
    ax4.set_xlim(0, 24)
    ax4.grid(alpha=0.3, which="both")
    ax4.legend(fontsize=8, ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1.0))

    # (1,2) 用地类型 × 小时 S-T 热力图（空间×时间联合）
    ax5 = fig.add_subplot(2, 3, 6)
    M = np.stack([class_h_mean[name] for name in CLASS_NAMES], axis=0)  # (6, 24)
    # 每行按自身最大值归一，凸显各用地的昼夜形状
    Mnorm = M / (M.max(axis=1, keepdims=True) + 1e-12)
    im5 = ax5.imshow(Mnorm, aspect="auto", cmap="viridis", vmin=0, vmax=1,
                     extent=[0, 24, len(CLASS_NAMES) - 0.5, -0.5])
    ax5.set_yticks(range(len(CLASS_NAMES)))
    ax5.set_yticklabels(CLASS_LABELS, fontsize=8)
    ax5.set_xticks(range(0, 25, 3))
    ax5.set_xlabel("小时 (h)")
    ax5.set_title("⑥ 用地类型×小时 噪声成本（行内归一）\n（空间×时间联合：何处、何时最敏感）")
    fig.colorbar(im5, ax=ax5, fraction=0.046, label="类内相对强度")
    # 标注绝对量级（每类全天峰值）到行尾
    for i, name in enumerate(CLASS_NAMES):
        ax5.text(24.3, i, f"峰值 {M[i].max():.3f}", va="center", fontsize=7, color="grey")

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig, dict(noise=noise, cost_z=cost_z, s_landuse=s_landuse,
                     z_val=z_val, z_idx=z_idx, vmax=vmax,
                     overall_h=overall_h, class_h_mean=class_h_mean)


def _print_summary(grid, info):
    nx, ny, nz, nt = grid.shape
    noise = info["noise"]
    print("=" * 64)
    print("噪声成本空间-时间异质性摘要")
    print("=" * 64)
    print(f"网格: {nx}×{ny}×{nz}×{nt}  参考高度 z={info['z_val']:.0f} m (层 {info['z_idx']})")
    print(f"噪声成本 @z: 范围 [{noise[:, :, info['z_idx'], :].min():.5f}, "
          f"{noise[:, :, info['z_idx'], :].max():.5f}]  均值 {noise[:, :, info['z_idx'], :].mean():.5f}")
    print(f"昼/夜共享颜色上限 vmax={info['vmax']:.5f}")
    print("各用地类全天峰值噪声成本（绝对，@z）：")
    for name, lab in zip(CLASS_NAMES, CLASS_LABELS):
        pk = float(np.max(info["class_h_mean"][name]))
        print(f"  {lab:8s} ({name:24s}) 峰值 {pk:.4f}")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser(description="噪声成本空间-时间异质性可视化")
    ap.add_argument("--save", action="store_true", help="保存到 output/统计/ 而非仅弹窗")
    ap.add_argument("--altitude", type=float, default=50.0, help="参考飞行高度 (m)")
    args = ap.parse_args()

    model, grid, landuse, rho_pop = _load_inputs()
    fig, info = build_figure(model, grid, landuse, rho_pop, altitude_m=args.altitude)
    _print_summary(grid, info)

    if args.save:
        out = MODULE_ROOT / "output" / "统计"
        out.mkdir(parents=True, exist_ok=True)
        path = out / "viz_noise_spatiotemporal.png"
        fig.savefig(path, dpi=130, bbox_inches="tight")
        print(f"已保存: {path}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
