#!/usr/bin/env python3
"""
土地利用可视化（landuse_map.npy，v2 = A+ 修复版）

- 主图：100×100 土地利用分类（1 住宅 / 2 商业 / 3 机构 / 4 工业 / 5 道路 / 6 绿地水域 / 0 未定）
- 右图：与交叉验证方案 B / C 的差异（一致 / 不一致）

只弹窗显示，不保存文件。数组轴序为 [ix, iy]（x=经度方向在前），显示需转置。
运行：python3 viz_landuse_map.py
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROC = Path(__file__).resolve().parents[2] / "data" / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]

CLASSES = {0: "未定", 1: "住宅", 2: "商业", 3: "机构", 4: "工业", 5: "道路", 6: "绿地/水域"}
COLORS = ["#dddddd", "#f4a582", "#d6604d", "#b2abd2", "#5aae61", "#878787", "#4dac26"]


def main() -> None:
    lu = np.load(PROC / "landuse_map.npy")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    cmap = ListedColormap(COLORS)
    norm = BoundaryNorm(np.arange(-0.5, 7.5, 1.0), cmap.N)

    im = axes[0].imshow(lu.T, origin="lower", extent=EXTENT, cmap=cmap, norm=norm, interpolation="nearest")
    axes[0].set_title("土地利用（v2，覆盖 99.2%）")
    cbar = fig.colorbar(im, ax=axes[0], ticks=range(7), fraction=0.046)
    cbar.ax.set_yticklabels([CLASSES[i] for i in range(7)])
    print("土地利用格数统计：")
    for k, v in zip(*np.unique(lu, return_counts=True)):
        print(f"  {CLASSES[int(k)]}({int(k)}): {int(v)} 格")

    # 与方案 B / C 交叉验证
    ref = lu.astype(int)
    vb = np.load(PROC / "landuse_map_b.npy").astype(int)
    vc = np.load(PROC / "landuse_map_c.npy").astype(int)
    agree = ((ref == vb) | (ref == vc)).astype(int)
    im2 = axes[1].imshow(agree.T, origin="lower", extent=EXTENT, cmap="coolwarm", vmin=0, vmax=1,
                         interpolation="nearest")
    axes[1].set_title("与方案 B/C 交叉验证\n(红=一致, 蓝=不一致)")
    same_b = float((ref == vb).mean()) * 100
    same_c = float((ref == vc).mean()) * 100
    print(f"与方案 B 一致率 {same_b:.1f}%，与方案 C 一致率 {same_c:.1f}%")

    for ax in axes:
        ax.set_xlabel("经度 (°E)")
        ax.set_ylabel("纬度 (°N)")
        ax.set_xlim(MINX, MAXX)
        ax.set_ylim(MINY, MAXY)
    fig.suptitle("研究区土地利用", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
