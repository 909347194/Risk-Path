#!/usr/bin/env python3
"""
潮汐密度可视化（rho_pop_3d.npy / rho_vehicle_3d.npy，96 个时相）

- 上排：人口潮汐 4 个代表时刻（t=0 凌晨 / t=32 上午 / t=56 下午 / t=80 晚间）
- 下排左：车辆潮汐同样 4 个时刻（小图）
- 下排中：全图总量随时间曲线（质量守恒校验）
- 下排右：峰值格 vs 低谷格的日内曲线（看潮汐幅度）

只弹窗显示，不保存文件。数组轴序 [ix, iy, t]，显示需转置前两维。
运行：python3 viz_tidal.py
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROC = Path(__file__).resolve().parents[2] / "data" / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]
TS = [0, 32, 56, 80]
NAME = {0: "t=0 凌晨", 32: "t=32 上午", 56: "t=56 下午", 80: "t=80 晚间"}


def main() -> None:
    rp = np.load(PROC / "rho_pop_3d.npy").astype(float)      # (100,100,96)
    rv = np.load(PROC / "rho_vehicle_3d.npy").astype(float)

    fig = plt.figure(figsize=(15, 9))
    # 人口潮汐 2×2
    vmax = rp.max()
    for k, t in enumerate(TS):
        ax = fig.add_subplot(3, 4, k + 1)
        im = ax.imshow(rp[:, :, t].T, origin="lower", extent=EXTENT, cmap="YlOrRd", vmin=0, vmax=vmax)
        ax.set_title(f"人口潮汐 {NAME[t]}", fontsize=10)
        ax.set_xlabel("经度 (°E)")
        if k == 0:
            ax.set_ylabel("纬度 (°N)")
    fig.colorbar(im, ax=fig.axes[:4], fraction=0.02, label="ρ_pop")

    # 车辆潮汐
    vmax_v = rv.max()
    for k, t in enumerate(TS):
        ax = fig.add_subplot(3, 4, 5 + k)
        ax.imshow(rv[:, :, t].T, origin="lower", extent=EXTENT, cmap="YlGnBu", vmin=0, vmax=vmax_v)
        ax.set_title(f"车辆潮汐 {NAME[t]}", fontsize=10)
        ax.set_xlabel("经度 (°E)")
        if k == 0:
            ax.set_ylabel("纬度 (°N)")

    # 总量守恒曲线
    ax = fig.add_subplot(3, 2, 5)
    tot_p = rp.sum(axis=(0, 1))
    tot_v = rv.sum(axis=(0, 1))
    ax.plot(tot_p, label=f"人口总量 (mean={tot_p.mean():.2f})", color="#d6604d")
    ax.plot(tot_v, label=f"车辆总量 (mean={tot_v.mean():.2f})", color="#4575b4")
    ax.set_xlabel("时相 t (0-95)")
    ax.set_ylabel("全图总量")
    ax.set_title("质量守恒校验：各时相总量应恒定")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    print(f"人口总量恒定性: min={tot_p.min():.4f} max={tot_p.max():.4f}（波动 {(tot_p.max()-tot_p.min())/tot_p.mean()*100:.4f}%）")
    print(f"车辆总量恒定性: min={tot_v.min():.4f} max={tot_v.max():.4f}")

    # 单格日内曲线
    ax = fig.add_subplot(3, 2, 6)
    ip = np.unravel_index(np.argmax(rp.sum(axis=2)), rp.shape[:2])
    iv = np.unravel_index(np.argmax(rv.sum(axis=2)), rv.shape[:2])
    ax.plot(rp[ip[0], ip[1], :], label=f"人口峰值格 (x={ip[0]},y={ip[1]})", color="#d6604d")
    ax.plot(rv[iv[0], iv[1], :], label=f"车辆峰值格 (x={iv[0]},y={iv[1]})", color="#4575b4")
    ax.set_xlabel("时相 t (0-95)")
    ax.set_ylabel("密度")
    ax.set_title("峰值格日内曲线（潮汐形态）")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

    fig.suptitle("潮汐人口 / 车辆密度（96 时相）", fontsize=13)
    # 手动留白：本图用了跨行 colorbar，tight_layout 会报警
    fig.subplots_adjust(left=0.06, right=0.93, top=0.92, bottom=0.06, hspace=0.38, wspace=0.25)
    plt.show()


if __name__ == "__main__":
    main()
