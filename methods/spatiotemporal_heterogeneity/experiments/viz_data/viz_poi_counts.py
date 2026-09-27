#!/usr/bin/env python3
"""
POI 可视化（poi_counts.npz 五类计数栅格 + poi_baidu.geojson 原始点位）

- 上排：五类 POI 计数栅格（residential / office / institution / transport / industrial）
- 下排左：五类叠加（点位大小=计数）
- 下排右：各类总量柱状图

只弹窗显示，不保存文件。数组轴序 [ix, iy]，显示需转置。
运行：python3 viz_poi_counts.py
"""
import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

DATA = Path(__file__).resolve().parents[2] / "data"
PROC = DATA / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]

CATS = ["residential", "office", "institution", "transport", "industrial"]
LABEL = {"residential": "住宅", "office": "办公商业", "institution": "机构", "transport": "交通", "industrial": "工业"}
COLORS = {"residential": "#f4a582", "office": "#d6604d", "institution": "#92c5de",
          "transport": "#4575b4", "industrial": "#5aae61"}


def main() -> None:
    npz = np.load(PROC / "poi_counts.npz")

    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    totals = {}
    for ax, cat in zip(axes.flat[:5], CATS):
        a = npz[cat]
        totals[cat] = float(a.sum())
        im = ax.imshow(a.T, origin="lower", extent=EXTENT, cmap="magma", interpolation="nearest")
        ax.set_title(f"{LABEL[cat]} ({cat})  Σ={totals[cat]:.0f}")
        fig.colorbar(im, ax=ax, fraction=0.046)
        ax.set_xlabel("经度 (°E)")
        ax.set_ylabel("纬度 (°N)")

    # 五类点位叠加（读原始 GeoJSON）
    ax = axes.flat[5]
    src = DATA / "01_raw" / "poi" / "poi_baidu.geojson"
    if src.exists():
        feats = json.loads(src.read_text(encoding="utf-8"))["features"]
        for cat in CATS:
            xs = [f["geometry"]["coordinates"][0] for f in feats if f["properties"].get("poi_class") == cat]
            ys = [f["geometry"]["coordinates"][1] for f in feats if f["properties"].get("poi_class") == cat]
            ax.scatter(xs, ys, s=4, alpha=0.55, c=COLORS[cat], label=f"{LABEL[cat]} {len(xs)}")
        ax.set_xlim(MINX, MAXX)
        ax.set_ylim(MINY, MAXY)
        ax.legend(loc="upper right", fontsize=8, markerscale=3)
        ax.set_title("原始 POI 点位（poi_baidu，WGS84）")
        ax.set_xlabel("经度 (°E)")
    else:
        ax.axis("off")

    print("POI 计数：")
    for c in CATS:
        print(f"  {LABEL[c]:6s} {totals[c]:.0f}")
    fig.suptitle("研究区 POI 五分类", fontsize=13)
    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
