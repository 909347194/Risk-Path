"""
Data Provision Pipeline - Orchestrator.

Provides one-click processing of all data types with automatic
synthetic/real path switching.

Pipeline stages:
    1. Landuse    -> landuse_map.npy
    2. Building   -> building_heights.npy
    3. Road       -> road_mask.npy
    4. Population -> base_pop_2d.npy
    5. POI        -> poi_counts.npz
    6. Tidal      -> rho_pop_3d.npy, rho_vehicle_3d.npy
    7. Weather    -> wind_field.npy, rain_data.npy

Usage:
    from data_provision.pipeline import DataPipeline

    # Synthetic mode
    pipeline = DataPipeline(data_type='synthetic')
    pipeline.run_all()

    # Real mode
    pipeline = DataPipeline(data_type='real')
    pipeline.run_all(grid=get_macro_grid())

    # Or switch globally
    from data_provision.paths import set_data_type
    set_data_type('synthetic')
    pipeline = DataPipeline()
    pipeline.run_all()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np

from .paths import (
    DataPaths,
    DataType,
    get_data_paths,
    get_data_type,
    set_data_type as _set_global_data_type,
    ensure_dirs,
)
from .population_resampler import (
    build_base_population,
    create_synthetic_base_population,
    resample_worldpop_to_grid,
    load_base_population,
)
from .poi_parser import (
    build_poi_counts,
    create_synthetic_poi_counts,
    parse_osm_poi_geojson,
    load_poi_counts,
)
from .spatiotemporal_tidal_model import (
    SpatiotemporalTidalModel,
    TidalModelConfig,
    build_dynamic_population_density,
    build_dynamic_vehicle_density,
)
from .landuse_builder import load_landuse_map, save_landuse_map
from .building_processor import (
    load_building_heights,
    estimate_building_heights_from_landuse,
    save_building_heights,
)
from .road_processor import load_road_mask, save_road_mask
from .weather_processor import load_wind_field, load_rain_data, save_wind_field, save_rain_data


@dataclass
class PipelineResult:
    """Results from running the data pipeline."""
    landuse: Optional[np.ndarray] = None
    building_heights: Optional[np.ndarray] = None
    road_mask: Optional[np.ndarray] = None
    base_population: Optional[np.ndarray] = None
    poi_counts: Optional[Dict[str, np.ndarray]] = None
    rho_population: Optional[np.ndarray] = None
    rho_vehicle: Optional[np.ndarray] = None
    wind_field: Optional[np.ndarray] = None
    rain_data: Optional[np.ndarray] = None
    paths: Optional[DataPaths] = None

    def summary(self) -> str:
        """Return a summary string of what was produced."""
        lines = [f"Data type: {self.paths.data_type if self.paths else 'unknown'}"]
        lines.append(f"Output dir: {self.paths.processed if self.paths else 'N/A'}")
        for name, arr in [
            ("landuse", self.landuse),
            ("building_heights", self.building_heights),
            ("road_mask", self.road_mask),
            ("base_population", self.base_population),
            ("poi_counts", self.poi_counts),
            ("rho_population", self.rho_population),
            ("rho_vehicle", self.rho_vehicle),
            ("wind_field", self.wind_field),
            ("rain_data", self.rain_data),
        ]:
            if arr is not None:
                if isinstance(arr, dict):
                    for k, v in arr.items():
                        lines.append(f"  {k}: {v.shape}")
                else:
                    lines.append(f"  {name}: {arr.shape}")
        return "\n".join(lines)


class DataPipeline:
    """
    Orchestrator for the entire data provision pipeline.

    Supports one-click synthetic/real switching via the `data_type` parameter
    or the global `set_data_type()` function.

    Typical usage:
        # Quick: process everything with synthetic data
        pipeline = DataPipeline(data_type='synthetic')
        result = pipeline.run_all()

        # Step-by-step control
        pipeline = DataPipeline(data_type='real', grid=my_grid)
        pipeline.run_landuse()
        pipeline.run_population(worldpop_tif='path/to/tif')
        result = pipeline.collect()
    """

    def __init__(
        self,
        data_type: Optional[DataType] = None,
        grid: Optional['GridSystem'] = None,
        paths: Optional[DataPaths] = None,
    ):
        """
        Initialize the pipeline.

        Args:
            data_type: 'synthetic' or 'real'. If None, uses global setting.
            grid: GridSystem instance. If None, auto-selected based on data type.
            paths: DataPaths instance. If None, derived from data_type.
        """
        # Set global data type if specified
        if data_type is not None:
            _set_global_data_type(data_type)

        self.grid = grid  # Will be lazily resolved
        self.paths = paths or get_data_paths()
        self.data_type = self.paths.data_type

        # Cached results
        self._landuse: Optional[np.ndarray] = None
        self._building: Optional[np.ndarray] = None
        self._road: Optional[np.ndarray] = None
        self._base_pop: Optional[np.ndarray] = None
        self._poi_counts: Optional[Dict[str, np.ndarray]] = None
        self._rho_pop: Optional[np.ndarray] = None
        self._rho_vehicle: Optional[np.ndarray] = None
        self._wind: Optional[np.ndarray] = None
        self._rain: Optional[np.ndarray] = None

    # ── Lazy grid resolution ────────────────────────────────────────────

    def _resolve_grid(self):
        """Lazily resolve the grid system based on data type."""
        if self.grid is not None:
            return self.grid
        try:
            from ..tensor_engine.grid_system import get_micro_grid, get_macro_grid
        except ImportError:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from tensor_engine.grid_system import get_micro_grid, get_macro_grid

        if self.data_type == 'synthetic':
            self.grid = get_micro_grid()
        else:
            self.grid = get_macro_grid()
        return self.grid

    # ── Individual pipeline stages ──────────────────────────────────────

    def run_landuse(self) -> np.ndarray:
        """
        Stage 1: Process landuse data.

        Synthetic: Loads from processed/synthetic/landuse_map.npy
        Real:      Reads shapefile, rasterizes to grid
        """
        ensure_dirs(self.data_type)
        self._landuse = load_landuse_map(
            paths=self.paths,
            grid_nx=self._resolve_grid().spatial.nx,
            grid_ny=self._resolve_grid().spatial.ny,
        )
        print(f"  ✓ landuse: {self._landuse.shape}")
        return self._landuse

    def run_building(self) -> np.ndarray:
        """
        Stage 2: Process building height data.

        Synthetic: Loads from processed/synthetic/building_heights.npy
        Real:      Reads shapefile, rasterizes heights
        """
        ensure_dirs(self.data_type)
        try:
            self._building = load_building_heights(
                paths=self.paths,
                grid_nx=self._resolve_grid().spatial.nx,
                grid_ny=self._resolve_grid().spatial.ny,
            )
        except FileNotFoundError:
            # Fallback: estimate from landuse
            if self._landuse is None:
                self.run_landuse()
            self._building = estimate_building_heights_from_landuse(
                self._landuse, paths=self.paths
            )
        print(f"  ✓ building: {self._building.shape}")
        return self._building

    def run_road(self) -> np.ndarray:
        """
        Stage 3: Process road network data.

        Synthetic: Loads from processed/synthetic/road_mask.npy
        Real:      Reads shapefile, rasterizes mask
        """
        ensure_dirs(self.data_type)
        self._road = load_road_mask(
            paths=self.paths,
            grid_nx=self._resolve_grid().spatial.nx,
            grid_ny=self._resolve_grid().spatial.ny,
        )
        print(f"  ✓ road: {self._road.shape}")
        return self._road

    def run_population(
        self,
        worldpop_tif: Optional[Union[str, Path]] = None,
        landuse: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Stage 4: Build base population.

        Synthetic: Creates from landuse
        Real:      Resamples WorldPop GeoTIFF
        """
        ensure_dirs(self.data_type)

        if self.data_type == 'synthetic':
            if landuse is None and self._landuse is None:
                self.run_landuse()
            self._base_pop = create_synthetic_base_population(
                grid=self._resolve_grid(),
                landuse=landuse or self._landuse,
                paths=self.paths,
            )
        else:
            if worldpop_tif is None:
                worldpop_tif = self.paths.worldpop_tif_path
            self._base_pop = build_base_population(
                worldpop_tif=worldpop_tif,
                grid=self._resolve_grid(),
                landuse=landuse or self._landuse,
                paths=self.paths,
            )
        print(f"  ✓ base_pop: {self._base_pop.shape}")
        return self._base_pop

    def run_poi(
        self,
        geojson_path: Optional[Union[str, Path]] = None,
        landuse: Optional[np.ndarray] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Stage 5: Build POI counts.

        Synthetic: Creates from landuse
        Real:      Parses OSM GeoJSON
        """
        ensure_dirs(self.data_type)

        if self.data_type == 'synthetic':
            if landuse is None and self._landuse is None:
                self.run_landuse()
            self._poi_counts = create_synthetic_poi_counts(
                grid=self._resolve_grid(),
                landuse=landuse or self._landuse,
                paths=self.paths,
            )
        else:
            if geojson_path is None:
                geojson_path = self.paths.osm_poi_geojson_path
            self._poi_counts = build_poi_counts(
                geojson_path=geojson_path,
                grid=self._resolve_grid(),
                landuse=landuse or self._landuse,
                paths=self.paths,
            )
        print(f"  ✓ poi_counts: {len(self._poi_counts)} categories")
        return self._poi_counts

    def run_tidal(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stage 6: Build spatiotemporal tidal density maps.

        Requires: base_population + poi_counts

        Produces:
            rho_population: (nx, ny, nt)
            rho_vehicle:    (nx, ny, nt)
        """
        if self._base_pop is None:
            self.run_population()
        if self._poi_counts is None:
            self.run_poi()

        model = SpatiotemporalTidalModel(grid=self._resolve_grid())

        self._rho_pop = model.build_population_density(
            self._base_pop, self._poi_counts,
            save_path=self.paths.rho_pop_path,
        )
        self._rho_vehicle = model.build_vehicle_density(
            self._base_pop, self._poi_counts,
            save_path=self.paths.rho_vehicle_path,
        )
        print(f"  ✓ rho_pop: {self._rho_pop.shape}")
        print(f"  ✓ rho_vehicle: {self._rho_vehicle.shape}")
        return self._rho_pop, self._rho_vehicle

    def run_weather(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Stage 7: Build weather data (wind + rain).

        Synthetic: Loads from 03_tensors/synthetic/
        Real:      Processes ERA5 NetCDF
        """
        ensure_dirs(self.data_type)
        nx = self._resolve_grid().spatial.nx
        ny = self._resolve_grid().spatial.ny
        nt = self._resolve_grid().temporal.nt

        self._wind = load_wind_field(
            paths=self.paths,
            grid_nx=nx, grid_ny=ny, grid_nt=nt,
        )
        self._rain = load_rain_data(
            paths=self.paths,
            grid_nx=nx, grid_ny=ny, grid_nt=nt,
        )
        print(f"  ✓ wind: {self._wind.shape}")
        print(f"  ✓ rain: {self._rain.shape}")
        return self._wind, self._rain

    # ── Full pipeline ───────────────────────────────────────────────────

    def run_all(
        self,
        worldpop_tif: Optional[Union[str, Path]] = None,
        geojson_path: Optional[Union[str, Path]] = None,
        landuse: Optional[np.ndarray] = None,
        skip_weather: bool = False,
    ) -> PipelineResult:
        """
        Run the entire data pipeline end-to-end.

        Stages executed in order:
            1. Landuse
            2. Building
            3. Road
            4. Population
            5. POI
            6. Tidal (population + vehicle density)
            7. Weather (wind + rain) — optional

        Args:
            worldpop_tif: Path to WorldPop GeoTIFF (real mode only)
            geojson_path: Path to OSM GeoJSON (real mode only)
            landuse: Pre-loaded landuse map (optional)
            skip_weather: If True, skip weather data processing

        Returns:
            PipelineResult with all generated data arrays
        """
        print(f"\n{'='*60}")
        print(f"Data Pipeline: {self.data_type.upper()} mode")
        print(f"Output: {self.paths.processed}")
        print(f"{'='*60}")

        self.run_landuse()
        self.run_building()
        self.run_road()
        self.run_population(worldpop_tif=worldpop_tif, landuse=landuse)
        self.run_poi(geojson_path=geojson_path)
        self.run_tidal()

        if not skip_weather:
            self.run_weather()

        result = self.collect()
        print(f"\n{'='*60}")
        print("Pipeline complete!")
        print(result.summary())
        print(f"{'='*60}")
        return result

    def collect(self) -> PipelineResult:
        """Collect all results into a PipelineResult."""
        return PipelineResult(
            landuse=self._landuse,
            building_heights=self._building,
            road_mask=self._road,
            base_population=self._base_pop,
            poi_counts=self._poi_counts,
            rho_population=self._rho_pop,
            rho_vehicle=self._rho_vehicle,
            wind_field=self._wind,
            rain_data=self._rain,
            paths=self.paths,
        )
