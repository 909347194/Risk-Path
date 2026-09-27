#!/usr/bin/env python3
"""
出行可视化（travel_user_counts.npz，手机信令 4 模式 × 10 时段）

- 上排：四模式全时段合计空间分布（pt_drive / bike / walking / subway）
- 下排左：各时段出行量曲线（分模式堆叠）
- 下排右：模式占比饼图

只弹窗显示，不保存文件。数组轴序 [ix, iy, t]，显示需转置前两维。
运行：python3 viz_travel.py
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

PROC = Path(__file__).resolve().parents[2] / "data" / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]

MODES = ["pt_drive", "bike", "walking", "subway"]
LABEL = {"pt_drive": "公交/驾车", "bike": "骑行", "walking": "步行", "subway": "地铁"}


def main() -> None:
    npz = np.load(PROC / "travel_user_counts.npz")
    slices = npz["time_slices"] if "time_slices" in npz.files else np.arange(len(npz[MODES[0]][0, 0]))

    fig, axes = plt.subplots(2, 3, figsize=(15, 8.6))
    totals = {}
    for ax, m in zip(axes.flat[:4], MODES):
        a = npz[m].sum(axis=2)          # (100,100)
        totals[m] = float(a.sum())
        im = ax.imshow(a.T, origin="lower", extent=EXTENT, cmap="viridis", interpolation="nearest")
        ax.set_title(f"{LABEL[m]} ({m})  Σ={totals[m]:,.0f}")
        fig.colorbar(im, ax=ax, fraction=0.046)
        ax.set_xlabel("经度 (°E)")

    # 各时段出行量（堆叠面积）
    ax = axes.flat[4]
    bottom = np.zeros(len(slices))
    for m in MODES:
        y = npz[m].sum(axis=(0, 1))
        ax.fill_between(range(len(slices)), bottom, bottom + y, alpha=0.75, label=LABEL[m])
        bottom += y
    ax.set_xlabel("时段序号 t")
    ax.set_ylabel("出行量")
    ax.set_title("分时段出行量")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # 模式占比
    ax = axes.flat[5]
    vals = [totals[m] for m in MODES]
    ax.pie(vals, labels=[LABEL[m] for m in MODES], autopct="%1.1f%%",
           colors=["#4575b4", "#fdae61", "#abdda4", "#d73027"], startangle=90)
    ax.set_title("出行模式占比")

    print("出行量（全时段合计）：")
    for m in MODES:
        print(f"  {LABEL[m]:8s} {totals[m]:>12,.0f}  ({totals[m]/sum(vals)*100:.1f}%)")
    print(f"  {'合计':8s} {sum(vals):>12,.0f}")
    fig.suptitle("研究区出行（手机信令）", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
