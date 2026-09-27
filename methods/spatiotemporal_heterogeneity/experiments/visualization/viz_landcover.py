#!/usr/bin/env python3
"""
土地覆盖可视化（landcover_fcs10_100x100.npy + landcover_impervious_frac_100x100.npy）

GLC_FCS30 10m 土地覆盖聚合到 100×100，作为土地利用的交叉验证基准。

- 左：土地覆盖分类栅格
- 中：不透水面比例
- 右：土地覆盖类别占比柱状图

只弹窗显示，不保存文件。数组轴序 [ix, iy]，显示需转置。
运行：python3 viz_landcover.py
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


def main() -> None:
    lc = np.load(PROC / "landcover_fcs10_100x100.npy")
    imp = np.load(PROC / "landcover_impervious_frac_100x100.npy").astype(float)

    vals, cnts = np.unique(lc, return_counts=True)
    print("土地覆盖类别格数：")
    for v, c in zip(vals, cnts):
        print(f"  类别 {int(v)}: {int(c)} 格")

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    n = max(len(vals), 2)
    cmap = ListedColormap(plt.cm.tab20(np.linspace(0, 1, n)))
    # GLC 类别码非连续（如 10/20/30...），先映射到 0..n-1 再上色
    idx = np.searchsorted(vals, lc)
    norm = BoundaryNorm(np.arange(-0.5, n + 0.5), cmap.N)

    im = axes[0].imshow(idx.T, origin="lower", extent=EXTENT, cmap=cmap, norm=norm, interpolation="nearest")
    cbar = fig.colorbar(im, ax=axes[0], ticks=range(n), fraction=0.046)
    cbar.ax.set_yticklabels([str(int(v)) for v in vals])
    axes[0].set_title("GLC_FCS30 土地覆盖（聚合后）")

    im2 = axes[1].imshow(imp.T, origin="lower", extent=EXTENT, cmap="YlOrRd", vmin=0, vmax=1,
                         interpolation="nearest")
    fig.colorbar(im2, ax=axes[1], fraction=0.046, label="不透水面比例")
    axes[1].set_title(f"不透水面比例（均值 {imp.mean():.2f}）")

    axes[2].bar([str(int(v)) for v in vals], cnts, color=cmap(np.linspace(0, 1, n)))
    axes[2].set_xlabel("土地覆盖类别")
    axes[2].set_ylabel("格数")
    axes[2].set_title("类别占比")

    for ax in axes[:2]:
        ax.set_xlabel("经度 (°E)")
        ax.set_ylabel("纬度 (°N)")
    fig.suptitle("土地覆盖（交叉验证基准）", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
