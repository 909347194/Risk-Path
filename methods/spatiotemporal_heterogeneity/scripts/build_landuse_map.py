#!/usr/bin/env python3
"""
方案 A：由 building 五类功能建筑面 + 路网生成 landuse_map.npy（真实模式）

编码（PROJECT_SPEC）：0=未定类 1=住宅 2=商业/办公 3=机构 4=工业 5=道路 6=绿地/水域

输入：
  data/01_raw/building/{Residential,Commercial,EducationalCultural,PublicServices,TechnologyIndustry}.shp
  data/01_raw/road/roadline_clip.shp（缺失时回退 road/osm_roads.geojson）

输出：
  data/02_processed/landuse_map.npy   (100,100) int32
  .openclaw/tmp/landuse_map_preview.png  预览图

栅格约定与 poi_parser.coordinate_to_grid_index(city_bounds) 一致：
  ix = int((x - minx) / (maxx - minx) * NX)   （WGS84 经度 -> x）
  iy = int((y - miny) / (maxy - miny) * NY)   （WGS84 纬度 -> y）
建筑物按「格心落在面内」判定；道路只填充未定类格子，避免覆盖建筑语义。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import shapefile
from matplotlib.path import Path as MplPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILDING_DIR = PROJECT_ROOT / "data" / "01_raw" / "building"
ROAD_SHP = PROJECT_ROOT / "data" / "01_raw" / "road" / "roadline_clip.shp"
ROAD_GEOJSON = PROJECT_ROOT / "data" / "01_raw" / "road" / "osm_roads.geojson"
OUT_NPY = PROJECT_ROOT / "data" / "02_processed" / "landuse_map.npy"
PREVIEW = Path(".openclaw/tmp/landuse_map_preview.png")

BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)
NX = NY = 100

# 图层 -> 土地利用编码
LAYER_CODE = {
    "Residential": 1,
    "Commercial": 2,
    "EducationalCultural": 3,
    "PublicServices": 3,
    "TechnologyIndustry": 4,
}


def cell_centers():
    minx, miny, maxx, maxy = BBOX
    xs = minx + (np.arange(NX) + 0.5) * (maxx - minx) / NX
    ys = miny + (np.arange(NY) + 0.5) * (maxy - miny) / NY
    return xs, ys


def _reader(path: Path) -> shapefile.Reader:
    """DBF 字段名/属性为 GBK 中文编码，优先 gbk，回退 utf-8。"""
    for enc in ("gbk", "utf-8"):
        try:
            return shapefile.Reader(str(path), encoding=enc)
        except Exception:
            continue
    raise RuntimeError(f"无法读取 shapefile: {path}")


def rasterize_polygons(shp_path: Path, code: int, grid: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> int:
    """把 shp 中的多边形面烧录到 grid（格心落在面内 -> code）。返回命中格数。"""
    sf = _reader(shp_path)
    before = int((grid == code).sum())
    xmin, ymin, xmax, ymax = BBOX
    step = (xmax - xmin) / NX / 4  # 边界采样步长约 1/4 格宽
    for shp in sf.shapes():
        if shp.shapeType not in (shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM):
            continue
        pts = np.asarray(shp.points, dtype=np.float64)
        if pts.size == 0:
            continue
        bx0, by0 = pts[:, 0].min(), pts[:, 1].min()
        bx1, by1 = pts[:, 0].max(), pts[:, 1].max()
        if bx1 < xmin or bx0 > xmax or by1 < ymin or by0 > ymax:
            continue
        # 多部件多边形：逐环构建 Path（外环/内环差异忽略，建筑面以内环极少）
        parts = list(shp.parts) + [len(pts)]
        for i in range(len(parts) - 1):
            ring = pts[parts[i]:parts[i + 1]]
            if len(ring) < 3:
                continue
            i0 = max(0, int((ring[:, 0].min() - xmin) / (xmax - xmin) * NX) - 1)
            i1 = min(NX, int((ring[:, 0].max() - xmin) / (xmax - xmin) * NX) + 2)
            j0 = max(0, int((ring[:, 1].min() - ymin) / (ymax - ymin) * NY) - 1)
            j1 = min(NY, int((ring[:, 1].max() - ymin) / (ymax - ymin) * NY) + 2)
            if i0 >= i1 or j0 >= j1:
                continue
            gx, gy = np.meshgrid(xs[i0:i1], ys[j0:j1], indexing="ij")
            cand = np.column_stack([gx.ravel(), gy.ravel()])
            inside = MplPath(ring).contains_points(cand)
            ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
            if inside.any():
                sel = inside.reshape(ii.shape)
                grid[ii[sel], jj[sel]] = code
            # 边界穿越判据：小建筑可能不盖格心，但与格子相交。沿边采样补命中
            for (x0, y0), (x1, y1) in zip(ring[:-1], ring[1:]):
                dist = max(abs(x1 - x0), abs(y1 - y0))
                k = max(2, int(dist / step) + 1)
                for x, y in zip(np.linspace(x0, x1, k), np.linspace(y0, y1, k)):
                    if not (xmin <= x <= xmax and ymin <= y <= ymax):
                        continue
                    ix = min(NX - 1, int((x - xmin) / (xmax - xmin) * NX))
                    jy = min(NY - 1, int((y - ymin) / (ymax - ymin) * NY))
                    grid[ix, jy] = code
    return int((grid == code).sum()) - before


def rasterize_lines_shp(shp_path: Path, grid: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> int:
    """道路 shp 线要素 -> code 5（沿线采样点所在格）。"""
    sf = _reader(shp_path)
    minx, miny, maxx, maxy = BBOX
    step = (maxx - minx) / NX / 3  # 采样步长约 1/3 格宽
    n = 0
    for shp in sf.shapes():
        pts = np.asarray(shp.points, dtype=np.float64)
        if pts.size == 0:
            continue
        for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
            dist = max(abs(x1 - x0), abs(y1 - y0))
            k = max(2, int(dist / step) + 1)
            for x, y in zip(np.linspace(x0, x1, k), np.linspace(y0, y1, k)):
                if not (minx <= x <= maxx and miny <= y <= maxy):
                    continue
                ix = min(NX - 1, int((x - minx) / (maxx - minx) * NX))
                iy = min(NY - 1, int((y - miny) / (maxy - miny) * NY))
                if grid[ix, iy] == 0:
                    grid[ix, iy] = 5
                    n += 1
    return n


def rasterize_lines_geojson(path: Path, grid: np.ndarray) -> int:
    data = json.loads(path.read_text(encoding="utf-8"))
    minx, miny, maxx, maxy = BBOX
    step = (maxx - minx) / NX / 3
    n = 0
    for feat in data.get("features", []):
        geom = feat.get("geometry") or {}
        coords = geom.get("coordinates")
        if not coords:
            continue
        lines = [coords] if geom.get("type") == "LineString" else coords
        for line in lines:
            arr = np.asarray(line, dtype=np.float64)
            if arr.ndim != 2 or len(arr) < 2:
                continue
            for (x0, y0), (x1, y1) in zip(arr[:-1], arr[1:]):
                dist = max(abs(x1 - x0), abs(y1 - y0))
                k = max(2, int(dist / step) + 1)
                for x, y in zip(np.linspace(x0, x1, k), np.linspace(y0, y1, k)):
                    if not (minx <= x <= maxx and miny <= y <= maxy):
                        continue
                    ix = min(NX - 1, int((x - minx) / (maxx - minx) * NX))
                    iy = min(NY - 1, int((y - miny) / (maxy - miny) * NY))
                    if grid[ix, iy] == 0:
                        grid[ix, iy] = 5
                        n += 1
    return n


def main() -> None:
    grid = np.zeros((NX, NY), dtype=np.int32)
    xs, ys = cell_centers()

    for layer, code in LAYER_CODE.items():
        shp = BUILDING_DIR / f"{layer}.shp"
        if not shp.exists() or shp.stat().st_size < 1000:
            print(f"[跳过] {layer}: shp 缺失或仍是 LFS 指针 ({shp.stat().st_size if shp.exists() else 'none'} bytes)")
            continue
        n = rasterize_polygons(shp, code, grid, xs, ys)
        print(f"[建筑] {layer} -> {code}: 新增 {n} 格")

    if ROAD_SHP.exists() and ROAD_SHP.stat().st_size > 1000:
        n = rasterize_lines_shp(ROAD_SHP, grid, xs, ys)
        print(f"[道路] roadline_clip.shp -> 5: 新增 {n} 格")
    elif ROAD_GEOJSON.exists():
        n = rasterize_lines_geojson(ROAD_GEOJSON, grid)
        print(f"[道路] osm_roads.geojson -> 5: 新增 {n} 格")

    OUT_NPY.parent.mkdir(parents=True, exist_ok=True)
    np.save(OUT_NPY, grid)
    vals, cnts = np.unique(grid, return_counts=True)
    print("类别分布:", dict(zip(vals.tolist(), cnts.tolist())))
    print("已保存:", OUT_NPY)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap, BoundaryNorm

        PREVIEW.parent.mkdir(parents=True, exist_ok=True)
        cmap = ListedColormap(["#f0f0f0", "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628"])
        norm = BoundaryNorm(np.arange(-0.5, 7.5, 1.0), cmap.N)
        fig, ax = plt.subplots(figsize=(7, 7))
        im = ax.imshow(grid.T, origin="lower", cmap=cmap, norm=norm, extent=[0, NX, 0, NY])
        ax.set_title("landuse_map (A: building+road)")
        fig.colorbar(im, ax=ax, ticks=range(7))
        fig.savefig(PREVIEW, dpi=110, bbox_inches="tight")
        print("预览图:", PREVIEW)
    except Exception as exc:
        print("[警告] 预览图生成失败:", exc)


if __name__ == "__main__":
    main()
