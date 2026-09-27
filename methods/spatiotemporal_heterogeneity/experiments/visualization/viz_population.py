#!/usr/bin/env python3
"""
人口可视化（base_pop_2d.npy，WorldPop 重采样，保总量 + y 翻转对齐）

- 左：100×100 人口密度栅格
- 右：人口累积曲线（看集中度）+ 统计

只弹窗显示，不保存文件。数组轴序 [ix, iy]，显示需转置。
运行：python3 viz_population.py
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROC = Path(__file__).resolve().parents[2] / "data" / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]


def main() -> None:
    pop = np.load(PROC / "base_pop_2d.npy").astype(float)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    im = axes[0].imshow(pop.T, origin="lower", extent=EXTENT, cmap="YlOrRd", interpolation="nearest")
    fig.colorbar(im, ax=axes[0], fraction=0.046, label="人口 (人/格)")
    axes[0].set_title(f"人口密度底图 base_pop_2d\n总量 {pop.sum():,.0f} 人，峰值 {pop.max():,.0f} 人/格")

    v = np.sort(pop.ravel())[::-1]
    cum = np.cumsum(v) / v.sum() * 100
    axes[1].plot(cum, color="#d6604d")
    axes[1].set_xlabel("格数（按人口降序）")
    axes[1].set_ylabel("累计人口占比 (%)")
    axes[1].set_title("人口集中度")
    for pct in (10, 20):
        axes[1].axvline(pct / 100 * pop.size, color="grey", ls=":", lw=1)
        axes[1].annotate(f"前{pct}%格\n{cum[int(pct/100*pop.size)-1]:.0f}%",
                         xy=(pct / 100 * pop.size, cum[int(pct / 100 * pop.size) - 1]),
                         xytext=(8, -20), textcoords="offset points", fontsize=9)
    axes[1].grid(alpha=0.3)
    print(f"人口总量 {pop.sum():,.0f}  非零格 {int((pop>0).sum())}  峰值 {pop.max():,.0f}")

    axes[0].set_xlabel("经度 (°E)")
    axes[0].set_ylabel("纬度 (°N)")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
