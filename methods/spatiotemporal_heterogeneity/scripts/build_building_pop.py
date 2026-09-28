#!/usr/bin/env python3
"""
补齐 02_processed 剩余基础矩阵（真实模式）：
  - building_heights.npy : (100,100) float32 米（每格取建筑最大 Height，峡谷/SVF 输入）
  - base_pop_2d.npy      : (100,100) float32 人（WorldPop tif 聚合，tfw 定位）

输入：
  data/01_raw/building/*.shp   （Height 字段，GBK DBF）
  data/01_raw/population/population.tif + population.tfw（~90m 格网）

网格约定与 poi/landuse 一致：ix = int((lon-minx)/(maxx-minx)*100)。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import shapefile
from matplotlib.path import Path as MplPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_landuse_map import BBOX, NX, NY  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDING_DIR = PROJECT_ROOT / "data" / "01_raw" / "building"
POP_TIF = PROJECT_ROOT / "data" / "01_raw" / "population" / "population.tif"
POP_TFW = PROJECT_ROOT / "data" / "01_raw" / "population" / "population.tfw"
OUT_BUILDING = PROJECT_ROOT / "data" / "02_processed" / "building_heights.npy"
OUT_POP = PROJECT_ROOT / "data" / "02_processed" / "base_pop_2d.npy"


def reader(path: Path):
    for enc in ("gbk", "utf-8"):
        try:
            return shapefile.Reader(str(path), encoding=enc)
        except Exception:
            continue
    raise RuntimeError(f"cannot read {path}")


def build_heights() -> np.ndarray:
    h = np.zeros((NX, NY), dtype=np.float32)
    minx, miny, maxx, maxy = BBOX
    step = (maxx - minx) / NX / 4
    for layer in ["Residential", "Commercial", "EducationalCultural", "PublicServices", "TechnologyIndustry"]:
        sf = reader(BUILDING_DIR / f"{layer}.shp")
        fields = [f[0] for f in sf.fields[1:]]
        hi = fields.index("Height")
        n = 0
        for rec, shp in zip(sf.iterRecords(), sf.iterShapes()):
            try:
                hv = float(rec[hi])
            except Exception:
                continue
            if hv <= 0:
                continue
            pts = np.asarray(shp.points, dtype=np.float64)
            if pts.size == 0:
                continue
            parts = list(shp.parts) + [len(pts)]
            for i in range(len(parts) - 1):
                ring = pts[parts[i]:parts[i + 1]]
                if len(ring) < 3:
                    continue
                i0 = max(0, int((ring[:, 0].min() - minx) / (maxx - minx) * NX) - 1)
                i1 = min(NX, int((ring[:, 0].max() - minx) / (maxx - minx) * NX) + 2)
                j0 = max(0, int((ring[:, 1].min() - miny) / (maxy - miny) * NY) - 1)
                j1 = min(NY, int((ring[:, 1].max() - miny) / (maxy - miny) * NY) + 2)
                if i0 >= i1 or j0 >= j1:
                    continue
                gx, gy = np.meshgrid(
                    minx + (np.arange(i0, i1) + 0.5) * (maxx - minx) / NX,
                    miny + (np.arange(j0, j1) + 0.5) * (maxy - miny) / NY,
                    indexing="ij",
                )
                cand = np.column_stack([gx.ravel(), gy.ravel()])
                inside = MplPath(ring).contains_points(cand)
                ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
                if inside.any():
                    sel = inside.reshape(ii.shape)
                    si, sj = ii[sel], jj[sel]
                    h[si, sj] = np.maximum(h[si, sj], hv)
                # 边界穿越补格（小建筑）
                for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
                    dist = max(abs(x1 - x0), abs(y1 - y0))
                    k = max(2, int(dist / step) + 1)
                    for x, y in zip(np.linspace(x0, x1, k), np.linspace(y0, y1, k)):
                        if minx <= x <= maxx and miny <= y <= maxy:
                            ix = min(NX - 1, int((x - minx) / (maxx - minx) * NX))
                            jy = min(NY - 1, int((y - miny) / (maxy - miny) * NY))
                            h[ix, jy] = max(h[ix, jy], hv)
                n += 1
        print(f"[building] {layer}: {n} 栋")
    print(f"building_heights: 覆盖 {int((h > 0).sum())}/{NX * NY} 格, mean={h[h > 0].mean():.1f}m max={h.max():.1f}m")
    return h


def build_population() -> np.ndarray:
    from PIL import Image

    tfw = [float(x) for x in POP_TFW.read_text().split()]
    a, d, e, f = tfw[0], tfw[3], tfw[4], tfw[5]  # x像素宽, y像素高, 左上x, 左上y
    arr = np.array(Image.open(POP_TIF), dtype=np.float64)  # (rows, cols)
    minx, miny, maxx, maxy = BBOX
    pop = np.zeros((NX, NY), dtype=np.float32)
    rows, cols = arr.shape
    for r in range(rows):
        for c in range(cols):
            v = arr[r, c]
            if not np.isfinite(v) or v == 0:
                continue
            lon = e + c * a
            lat = f + r * d
            if not (minx <= lon <= maxx and miny <= lat <= maxy):
                continue
            ix = min(NX - 1, int((lon - minx) / (maxx - minx) * NX))
            iy = min(NY - 1, int((lat - miny) / (maxy - miny) * NY))
            pop[ix, iy] += v
    print(f"base_pop_2d: 覆盖 {int((pop > 0).sum())}/{NX * NY} 格, 合计 {pop.sum():.0f} 人, max={pop.max():.0f}/格")
    return pop


def main() -> None:
    np.save(OUT_BUILDING, build_heights())
    np.save(OUT_POP, build_population())
    print("已保存:", OUT_BUILDING, OUT_POP)


if __name__ == "__main__":
    main()
