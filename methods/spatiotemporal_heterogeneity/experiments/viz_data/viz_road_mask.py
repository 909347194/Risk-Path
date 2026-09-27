#!/usr/bin/env python3
"""
路网可视化（road_mask.npy）+ 人口底图（base_pop_2d.npy）叠加

- 左：road_mask（格心距路网 ≤24m 的邻域格）
- 右：路网叠加在人口底图上，看路网与人口的空间关系

只弹窗显示，不保存文件。数组轴序 [ix, iy]，显示需转置。
运行：python3 viz_road_mask.py
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
    road = np.load(PROC / "road_mask.npy").astype(bool)
    pop = np.load(PROC / "base_pop_2d.npy").astype(float)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    axes[0].imshow(road.T, origin="lower", extent=EXTENT, cmap="Greys", interpolation="nearest")
    axes[0].set_title(f"路网邻域掩码（True {int(road.sum())} 格 / {road.size} = {road.mean()*100:.1f}%）")

    im = axes[1].imshow(pop.T, origin="lower", extent=EXTENT, cmap="YlGnBu", interpolation="nearest")
    fig.colorbar(im, ax=axes[1], fraction=0.046, label="人口 (人/格)")
    axes[1].imshow(np.ma.masked_where(~road.T, road.T), origin="lower", extent=EXTENT,
                   cmap="Reds", alpha=0.35, interpolation="nearest")
    axes[1].set_title("路网（红）叠加人口底图")

    for ax in axes:
        ax.set_xlabel("经度 (°E)")
        ax.set_ylabel("纬度 (°N)")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
