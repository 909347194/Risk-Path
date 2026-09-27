#!/usr/bin/env python3
"""
建筑五类面 + 研究区范围可视化（原始 SHP 数据，01_raw）

- 左：五类建筑面着色（Commercial / Residential / EducationalCultural / PublicServices / TechnologyIndustry）
- 右：Height 字段散点（建筑高度原始值）

用于核对原始建筑数据与研究区边界。只弹窗显示，不保存文件。
运行：python3 viz_buildings_raw.py
"""
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

RAW = Path(__file__).resolve().parents[2] / "data" / "01_raw"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036

LAYERS = {
    "Commercial": "#d6604d",
    "Residential": "#f4a582",
    "EducationalCultural": "#92c5de",
    "PublicServices": "#b2abd2",
    "TechnologyIndustry": "#5aae61",
}


def read_layer(name):
    import shapefile
    for enc in ("gbk", "utf-8"):
        try:
            sf = shapefile.Reader(str(RAW / "building" / name), encoding=enc)
            break
        except Exception:
            continue
    fields = [f[0] for f in sf.fields[1:]]
    hi = fields.index("Height") if "Height" in fields else 0
    out = []
    for sr in sf.iterShapeRecords():
        try:
            geom = sr.shape.__geo_interface__
            h = float(sr.record[hi])
        except Exception:
            continue
        if geom:
            out.append((geom, h))
    return out


def main() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.2))
    total = 0
    for name, color in LAYERS.items():
        feats = read_layer(name)
        total += len(feats)
        for k, (geom, h) in enumerate(feats):
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                ring = np.asarray(poly[0])
                axes[0].add_patch(MplPolygon(ring, closed=True, facecolor=color,
                                             edgecolor="none", alpha=0.75,
                                             label=name if k == 0 else None))
        hs = [h for _, h in feats]
        print(f"  {name:20s} {len(feats):5d} 栋  Height {min(hs):.1f}–{max(hs):.1f} m")
    print(f"  合计 {total} 栋")

    axes[0].plot([MINX, MAXX, MAXX, MINX, MINX], [MINY, MINY, MAXY, MAXY, MINY],
                 "k--", lw=1, label="研究区范围")
    axes[0].set_xlim(MINX, MAXX)
    axes[0].set_ylim(MINY, MAXY)
    axes[0].set_xlabel("经度 (°E)")
    axes[0].set_ylabel("纬度 (°N)")
    axes[0].set_title(f"建筑五类面（{total} 栋）")
    axes[0].legend(loc="upper right", fontsize=8)

    # 高度散点
    for name, color in LAYERS.items():
        feats = read_layer(name)
        xs, ys, hs = [], [], []
        for geom, h in feats:
            try:
                polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
                ring = np.asarray(polys[0][0])
                xs.append(ring[:, 0].mean())
                ys.append(ring[:, 1].mean())
                hs.append(h)
            except Exception:
                continue
        axes[1].scatter(xs, ys, c=[color] * len(xs), s=[max(v, 1) * 0.35 for v in hs],
                        alpha=0.5, label=name)
    axes[1].set_xlim(MINX, MAXX)
    axes[1].set_ylim(MINY, MAXY)
    axes[1].set_xlabel("经度 (°E)")
    axes[1].set_ylabel("纬度 (°N)")
    axes[1].set_title("Height 字段（点大小=高度）")
    axes[1].legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
