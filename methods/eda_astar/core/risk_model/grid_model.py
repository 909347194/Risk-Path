from __future__ import annotations

from pathlib import Path
from typing import Iterable

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from shapely.geometry import box, Polygon

DEFAULT_TARGET_CRS = "EPSG:3857"


def load_building_shapefiles(directory: Path, target_crs: str = DEFAULT_TARGET_CRS) -> gpd.GeoDataFrame:
    directory = Path(directory)
    shapefiles = sorted(directory.rglob("*.shp"))
    if not shapefiles:
        raise FileNotFoundError(f"No shapefiles found under {directory}")

    gdfs = [gpd.read_file(path) for path in shapefiles]
    buildings = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs=gdfs[0].crs)

    if buildings.crs is None:
        raise ValueError("Building data has no CRS")

    if buildings.crs.to_string() != target_crs:
        buildings = buildings.to_crs(target_crs)

    height_field = next(
        (f for f in ["Height", "Height_1", "高度", "height"] if f in buildings.columns),
        None,
    )
    if height_field is None:
        buildings["height"] = 0.0
    else:
        buildings["height"] = buildings[height_field].astype(float).fillna(0.0)

    return buildings[["geometry", "height"]]


class Grid3D:
    def __init__(
        self,
        minx: float,
        miny: float,
        maxx: float,
        maxy: float,
        cell_size: float = 80.0,
        layer_altitudes: Iterable[float] = (30.0, 60.0, 90.0, 120.0),
        target_crs: str = DEFAULT_TARGET_CRS,
    ):
        self.minx = float(minx)
        self.miny = float(miny)
        self.maxx = float(maxx)
        self.maxy = float(maxy)
        self.cell_size = float(cell_size)
        self.target_crs = target_crs
        self.layer_altitudes = np.array(list(layer_altitudes), dtype=float)

        self.width = int(np.ceil((self.maxx - self.minx) / self.cell_size))
        self.height = int(np.ceil((self.maxy - self.miny) / self.cell_size))
        self.cell_area = self.cell_size * self.cell_size

        self._centers = None
        self._cell_polygons = None

    @classmethod
    def from_sources(
        cls,
        buildings: gpd.GeoDataFrame,
        population_raster: Path,
        cell_size: float = 80.0,
        padding: float = 160.0,
        target_crs: str = DEFAULT_TARGET_CRS,
    ) -> "Grid3D":
        if buildings.crs is None:
            raise ValueError("Building GeoDataFrame must have CRS")
        if buildings.crs.to_string() != target_crs:
            buildings = buildings.to_crs(target_crs)

        with rasterio.open(population_raster) as src:
            pop_bounds = src.bounds
            pop_crs = src.crs
            if pop_crs is None:
                raise ValueError("Population raster has no CRS")

            if pop_crs.to_string() != target_crs:
                transformer = Transformer.from_crs(pop_crs, target_crs, always_xy=True)
                pop_minx, pop_miny = transformer.transform(pop_bounds.left, pop_bounds.bottom)
                pop_maxx, pop_maxy = transformer.transform(pop_bounds.right, pop_bounds.top)
            else:
                pop_minx, pop_miny, pop_maxx, pop_maxy = pop_bounds.left, pop_bounds.bottom, pop_bounds.right, pop_bounds.top

        b_minx, b_miny, b_maxx, b_maxy = buildings.total_bounds
        minx = min(b_minx, pop_minx) - padding
        miny = min(b_miny, pop_miny) - padding
        maxx = max(b_maxx, pop_maxx) + padding
        maxy = max(b_maxy, pop_maxy) + padding

        return cls(minx=minx, miny=miny, maxx=maxx, maxy=maxy, cell_size=cell_size, target_crs=target_crs)

    @property
    def centers(self) -> np.ndarray:
        if self._centers is None:
            xs = self.minx + self.cell_size * (np.arange(self.width) + 0.5)
            ys = self.maxy - self.cell_size * (np.arange(self.height) + 0.5)
            grid_x, grid_y = np.meshgrid(xs, ys)
            self._centers = np.stack([grid_x, grid_y], axis=-1)
        return self._centers

    @property
    def lonlat_centers(self) -> np.ndarray:
        transformer = Transformer.from_crs(self.target_crs, "EPSG:4326", always_xy=True)
        flat = self.centers.reshape(-1, 2)
        lon, lat = transformer.transform(flat[:, 0], flat[:, 1])
        return np.stack([lon, lat], axis=-1).reshape(self.height, self.width, 2)

    @property
    def cell_polygons(self) -> np.ndarray:
        if self._cell_polygons is None:
            polys = []
            for row in range(self.height):
                y1 = self.maxy - row * self.cell_size
                y0 = y1 - self.cell_size
                for col in range(self.width):
                    x0 = self.minx + col * self.cell_size
                    x1 = x0 + self.cell_size
                    polys.append(box(x0, y0, x1, y1))
            self._cell_polygons = np.array(polys, dtype=object)
        return self._cell_polygons

    def to_geodataframe(self) -> gpd.GeoDataFrame:
        return gpd.GeoDataFrame(
            {"row": np.repeat(np.arange(self.height), self.width),
             "col": np.tile(np.arange(self.width), self.height),
             "geometry": self.cell_polygons},
            crs=self.target_crs,
        )

    def summary(self) -> str:
        return (
            f"Grid3D: {self.width} x {self.height} cells, cell_size={self.cell_size}m, "
            f"layers={list(self.layer_altitudes)}m, bounds=({self.minx:.0f},{self.miny:.0f},{self.maxx:.0f},{self.maxy:.0f})"
        )
