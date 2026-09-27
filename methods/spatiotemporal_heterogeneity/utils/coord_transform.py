#!/usr/bin/env python3
"""
坐标工具：网格↔经纬度、基准纠偏（GCJ02/BD09↔WGS84）、局部米制换算。

定位：spatiotemporal_heterogeneity 全模块的坐标口径单一来源（single source of truth）。
- 网格约定与 build_landuse_map.py / poi_parser.coordinate_to_grid_index 一致：
    ix = int((lon - minx) / (maxx - minx) * NX)   （iy 同理，iy=0 在南侧）
- 研究区尺度（~5km）用局部等距圆柱（equirectangular）换算米制，误差 <0.1%，
  无需完整投影库；若扩展到 >25km 域，再考虑 UTM 49N (EPSG:32649)。
- GCJ02 纠偏算法与 scripts/fetch_baidu_poi.py 同源（WGS84 火星坐标偏差）。
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

# ── 研究区与网格（与 build_landuse_map.py 保持一致）───────────────────
BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)  # minx, miny, maxx, maxy
NX = NY = 100

MINX, MINY, MAXX, MAXY = BBOX
LAT0 = (MINY + MAXY) / 2.0
M_PER_DEG_LAT = 110574.0
M_PER_DEG_LON = 111320.0 * math.cos(math.radians(LAT0))


def cell_size_m() -> Tuple[float, float]:
    """真实格宽（米）：(dx, dy)。注意与 config 的 50m 标称值存在 ~4% 偏差。"""
    return ((MAXX - MINX) / NX * M_PER_DEG_LON, (MAXY - MINY) / NY * M_PER_DEG_LAT)


def lonlat_to_grid(lon, lat) -> Tuple[np.ndarray, np.ndarray]:
    """经纬度 -> 格索引 (ix, iy)，越界裁剪到 [0, N-1]。支持标量/数组。"""
    ix = np.clip(((np.asarray(lon) - MINX) / (MAXX - MINX) * NX).astype(np.int64), 0, NX - 1)
    iy = np.clip(((np.asarray(lat) - MINY) / (MAXY - MINY) * NY).astype(np.int64), 0, NY - 1)
    return ix, iy


def grid_to_lonlat(ix, iy) -> Tuple[np.ndarray, np.ndarray]:
    """格索引 -> 格心经纬度。支持标量/数组。"""
    lon = MINX + (np.asarray(ix) + 0.5) * (MAXX - MINX) / NX
    lat = MINY + (np.asarray(iy) + 0.5) * (MAXY - MINY) / NY
    return lon, lat


def lonlat_to_local_m(lon, lat) -> Tuple[np.ndarray, np.ndarray]:
    x = (np.asarray(lon, dtype=np.float64) - MINX) * M_PER_DEG_LON
    y = (np.asarray(lat, dtype=np.float64) - MINY) * M_PER_DEG_LAT
    return x, y


# ── GCJ02 基准纠偏（高德/腾讯坐标 -> WGS84）──────────────────────────
_A = 6378245.0
_EE = 0.00669342162296594323


def _transform_lat(x: float, y: float) -> float:
    r = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    r += (160.0 * math.sin(y / 12.0 * math.pi) + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return r


def _transform_lng(x: float, y: float) -> float:
    r = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    r += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    r += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    r += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return r


def gcj02_offset(lat: float, lng: float) -> Tuple[float, float]:
    """GCJ02 相对 WGS84 的加密偏移量（dlat, dlng，单位：度）。"""
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    rad = lat / 180.0 * math.pi
    magic = math.sin(rad)
    magic = 1 - _EE * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (_A / sqrt_magic * math.cos(rad) * math.pi)
    return d_lat, d_lng


def gcj02_to_wgs84(lat: float, lng: float) -> Tuple[float, float]:
    """GCJ02（高德/腾讯）-> WGS84。单次偏移逆变换，米级精度足够 POI 落格。"""
    d_lat, d_lng = gcj02_offset(lat, lng)
    return lat - d_lat, lng - d_lng


def wgs84_to_gcj02(lat: float, lng: float) -> Tuple[float, float]:
    """WGS84 -> GCJ02（正向加密）。"""
    d_lat, d_lng = gcj02_offset(lat, lng)
    return lat + d_lat, lng + d_lng


if __name__ == "__main__":
    dx, dy = cell_size_m()
    print(f"BBOX={BBOX}")
    print(f"真实格宽: dx={dx:.1f}m, dy={dy:.1f}m  (config 标称 50m，偏差 {(50-dx)/50*100:+.1f}%/格)")
    lon, lat = grid_to_lonlat(np.array([0, 50, 99]), np.array([0, 50, 99]))
    print("格心抽样:", [(round(float(a), 5), round(float(b), 5)) for a, b in zip(lon, lat)])
    ix, iy = lonlat_to_grid(lon, lat)
    print("往返一致:", bool(np.all(ix == [0, 50, 99]) and np.all(iy == [0, 50, 99])))
    print("GCJ02 抽样(广州塔附近):", tuple(round(v, 6) for v in gcj02_to_wgs84(23.1066, 113.3245)))
