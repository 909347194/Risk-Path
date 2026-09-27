#!/usr/bin/env python3
"""
建筑高度可视化（building_heights.npy）

- 左：100×100 格内最大建筑高度（all_touched + max 池化，已修正 y 镜像）
- 右：高度直方图 + 建筑格覆盖率

只弹窗显示，不保存文件。数组轴序 [ix, iy]，显示需转置。
运行：python3 viz_building_heights.py
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
    h = np.load(PROC / "building_heights.npy").astype(float)
    nz = h[h > 0]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))

    im = axes[0].imshow(h.T, origin="lower", extent=EXTENT, cmap="YlOrRd", interpolation="nearest")
    fig.colorbar(im, ax=axes[0], fraction=0.046, label="高度 (m)")
    axes[0].set_title(f"建筑高度（格内最大值）\n非零 {nz.size} 格 / 共 {h.size} 格 = {nz.size/h.size*100:.1f}%")

    axes[1].hist(nz, bins=40, color="#d6604d", edgecolor="white")
    axes[1].axvline(np.median(nz), color="k", ls="--", lw=1, label=f"p50 = {np.median(nz):.1f} m")
    axes[1].axvline(np.percentile(nz, 90), color="navy", ls="--", lw=1, label=f"p90 = {np.percentile(nz, 90):.1f} m")
    axes[1].set_xlabel("建筑高度 (m)")
    axes[1].set_ylabel("格数")
    axes[1].set_title("高度分布")
    axes[1].legend()
    print(f"高度统计：p50={np.median(nz):.1f}m  p90={np.percentile(nz,90):.1f}m  max={nz.max():.1f}m")

    axes[0].set_xlabel("经度 (°E)")
    axes[0].set_ylabel("纬度 (°N)")
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
