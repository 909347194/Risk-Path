#!/usr/bin/env python3
"""
真实数据（01_raw）→ 02_processed 补齐处理。

生成 pipeline 约定但尚缺失的产物：
  building_heights.npy   (100,100) float32  建筑最大高度（Height 字段，五类面合并）
  road_mask.npy          (100,100) bool     道路掩膜（格心距路网≤24m，与 landuse v2 同判据）
  base_pop_2d.npy        (100,100) float32  基础人口（WorldPop 栅格重采样，保总量）
  rho_pop_3d.npy         (100,100,96)       潮汐人口密度（质量守恒 POI 引力模型）
  rho_vehicle_3d.npy     (100,100,96)       潮汐车辆密度

已就绪不重建：landuse_map.npy(v2)、poi_counts.npz、travel_user_counts.npz、base_vehicle_2d.npy、
landcover_*.npy
缺失待外部数据：wind_field.npy / rain_data.npy（ERA5，P_crash 动态因子）
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from build_landuse_map import BBOX, NX, NY  # noqa: E402

RAW = PROJECT_ROOT / "data/01_raw"
PROC = PROJECT_ROOT / "data/02_processed"
BUILDING_DIR = RAW / "building"
POP_TIF = RAW / "population" / "population.tif"

LAYER_CODE = {"Residential": 1, "Commercial": 2, "EducationalCultural": 3,
              "PublicServices": 3, "TechnologyIndustry": 4}

minx, miny, maxx, maxy = BBOX


def build_heights() -> np.ndarray:
    """五类建筑面 Height 字段 -> 100×100 最大高度（细栅格烧录 + max 池化）。"""
    import shapefile
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    FINE = 10  # m
    mx = 111320.0 * np.cos(np.deg2rad((miny + maxy) / 2))
    my = 110574.0
    dx_deg = FINE / mx
    dy_deg = FINE / my
    nxf = int(np.ceil((maxx - minx) / dx_deg))
    nyf = int(np.ceil((maxy - miny) / dy_deg))
    transform = from_origin(minx, maxy, dx_deg, dy_deg)

    feats = []
    for layer in LAYER_CODE:
        shp_path = BUILDING_DIR / f"{layer}.shp"
        if not shp_path.exists() or shp_path.stat().st_size < 1000:
            print(f"  [跳过] {layer}")
            continue
        sf = None
        for enc in ("gbk", "utf-8"):
            try:
                sf = shapefile.Reader(str(shp_path), encoding=enc)
                break
            except Exception:
                continue
        fields = [f[0] for f in sf.fields[1:]]
        hcol = "Height" if "Height" in fields else ("Height_1" if "Height_1" in fields else None)
        if hcol is None:
            print(f"  [警告] {layer} 无 Height 字段，跳过")
            continue
        hi = fields.index(hcol)
        cnt = 0
        for shp_rec in sf.iterShapeRecords():
            try:
                geom = shp_rec.shape.__geo_interface__
                h = float(shp_rec.record[hi])
            except Exception:
                continue
            if h > 0 and geom:
                feats.append((geom, h))
                cnt += 1
        print(f"  [建筑] {layer}: {cnt} 栋")

    feats.sort(key=lambda t: t[1])          # 矮→高烧录，高者覆盖 = 格内最大值
    fine = rasterize(feats, out_shape=(nyf, nxf), transform=transform,
                     fill=0.0, dtype=np.float32, all_touched=True)  # 与土地利用“边界穿越”口径一致；矮→高烧录取格内最大
    # max 池化到 100×100；注意细栅格 row0=北，而格网 iy=0=南，y 需镜像
    heights = np.zeros((NX, NY), dtype=np.float32)
    for i in range(NX):
        x0 = int(i * nxf / NX); x1 = max(x0 + 1, int((i + 1) * nxf / NX))
        for j in range(NY):
            ya = int(j * nyf / NY); yb = max(ya + 1, int((j + 1) * nyf / NY))
            heights[i, j] = fine[nyf - yb:nyf - ya, x0:x1].max()
    return heights


def build_road_mask() -> np.ndarray:
    from refine_landuse_map import load_road_segments, road_cells
    return road_cells(load_road_segments())


def build_base_pop() -> np.ndarray:
    from data_provision.population_resampler import resample_worldpop_to_grid
    from tensor_engine.grid_system import get_macro_grid
    grid = get_macro_grid()
    return resample_worldpop_to_grid(
        tif_path=POP_TIF, grid=grid,
        city_bounds=BBOX, bounds_crs="EPSG:4326",
        flip_y=True, preserve_total=True, save=False,
    )


def build_tidal(base_pop: np.ndarray, base_vehicle: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from data_provision.spatiotemporal_tidal_model import SpatiotemporalTidalModel, TidalModelConfig
    from tensor_engine.grid_system import get_macro_grid

    cfg = TidalModelConfig()
    names = {f.name for f in dataclasses.fields(TidalModelConfig)}
    if "N_total_pop" in names:
        cfg.N_total_pop = float(base_pop.sum())
    if "N_total_veh" in names:
        cfg.N_total_veh = float(base_vehicle.sum())
    model = SpatiotemporalTidalModel(grid=get_macro_grid(), config=cfg)
    poi = dict(np.load(PROC / "poi_counts.npz"))
    rho_pop = model.build_population_density(base_pop, poi, save_path=None)
    rho_veh = model.build_vehicle_density(base_vehicle, poi, save_path=None)
    return rho_pop, rho_veh


def check(name: str, arr: np.ndarray) -> None:
    nan = int(np.isnan(arr).sum()) if arr.dtype.kind == "f" else 0
    print(f"  {name}: shape={arr.shape} dtype={arr.dtype} min={np.nanmin(arr):.4g} "
          f"max={np.nanmax(arr):.4g} sum={np.nansum(arr):.4g} nan={nan}")


def main() -> None:
    PROC.mkdir(parents=True, exist_ok=True)

    print("== 1/4 building_heights ==")
    h = build_heights()
    np.save(PROC / "building_heights.npy", h)
    check("building_heights", h)

    print("== 2/4 road_mask ==")
    r = build_road_mask()
    np.save(PROC / "road_mask.npy", r)
    check("road_mask", r)

    print("== 3/4 base_pop ==")
    p = build_base_pop()
    np.save(PROC / "base_pop_2d.npy", p)
    check("base_pop_2d", p)

    print("== 4/4 tidal (rho_pop / rho_vehicle) ==")
    base_vehicle = np.load(PROC / "base_vehicle_2d.npy").astype(np.float32)
    rp, rv = build_tidal(p.astype(np.float32), base_vehicle)
    np.save(PROC / "rho_pop_3d.npy", rp)
    np.save(PROC / "rho_vehicle_3d.npy", rv)
    check("rho_pop_3d", rp)
    check("rho_vehicle_3d", rv)

    print("\n== 缺口提醒 ==")
    print("  wind_field.npy / rain_data.npy（ERA5）仍缺：P_crash 的风×雨动态因子无法生成，")
    print("  TensorBuilder 需要它们才能组装 Cost_total(100,100,12,96)。")


if __name__ == "__main__":
    main()
