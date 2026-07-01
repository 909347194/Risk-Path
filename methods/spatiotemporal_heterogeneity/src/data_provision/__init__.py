"""
Data provision layer.

Responsibility:
    Raw/synthetic GIS-like inputs -> aligned NumPy matrices.

This layer should not build risk/cost tensors and should not run path planning.
Those responsibilities belong to tensor_engine and algorithms respectively.

Enhancement:
    Added full support for distinguishing between synthetic and real data processing.
    Synthetic data paths contain 'synthetic' in their directory structure.

Key features:
    - One-click switching between synthetic and real data via set_data_type()
    - Automatic path resolution through DataPaths
    - Full pipeline orchestration via DataPipeline
    - Processors for: landuse, building, road, population, POI, weather (wind/rain)
"""

from .paths import (
    DataPaths,
    DataType,
    get_data_paths,
    get_data_type,
    set_data_type,
    ensure_dirs,
)
from .landuse_builder import (
    load_landuse_map,
    save_landuse_map,
)
from .building_processor import (
    load_building_heights,
    estimate_building_heights_from_landuse,
    save_building_heights,
)
from .road_processor import (
    load_road_mask,
    save_road_mask,
)
from .weather_processor import (
    load_wind_field,
    load_rain_data,
    save_wind_field,
    save_rain_data,
)
from .poi_parser import (
    POI_CATEGORIES,
    build_poi_counts,
    classify_poi,
    create_synthetic_poi_counts,
    load_poi_counts,
    parse_osm_poi_geojson,
    save_poi_counts,
)
from .population_resampler import (
    build_base_population,
    create_synthetic_base_population,
    load_base_population,
    resample_worldpop_to_grid,
    save_base_population,
)
from .spatiotemporal_tidal_model import (
    SpatiotemporalTidalModel,
    SpatiotemporalTidalModelforPopulationDensity,
    SpatiotemporalTidalModelforTrafficDensity,
    TidalModelConfig,
    build_dynamic_population_density,
    build_dynamic_vehicle_density,
    population_activation,
    traffic_activation,
)
from .pipeline import (
    DataPipeline,
    PipelineResult,
)

__all__ = [
    # Path switching
    "DataPaths",
    "DataType",
    "get_data_paths",
    "get_data_type",
    "set_data_type",
    "ensure_dirs",

    # Landuse
    "load_landuse_map",
    "save_landuse_map",

    # Building
    "load_building_heights",
    "estimate_building_heights_from_landuse",
    "save_building_heights",

    # Road
    "load_road_mask",
    "save_road_mask",

    # Weather
    "load_wind_field",
    "load_rain_data",
    "save_wind_field",
    "save_rain_data",

    # POI
    "POI_CATEGORIES",
    "build_poi_counts",
    "classify_poi",
    "create_synthetic_poi_counts",
    "load_poi_counts",
    "parse_osm_poi_geojson",
    "save_poi_counts",

    # Population
    "build_base_population",
    "create_synthetic_base_population",
    "load_base_population",
    "resample_worldpop_to_grid",
    "save_base_population",

    # Tidal model
    "SpatiotemporalTidalModel",
    "SpatiotemporalTidalModelforPopulationDensity",
    "SpatiotemporalTidalModelforTrafficDensity",
    "TidalModelConfig",
    "build_dynamic_population_density",
    "build_dynamic_vehicle_density",
    "population_activation",
    "traffic_activation",

    # Pipeline orchestrator
    "DataPipeline",
    "PipelineResult",
]

# Re-export for backward compatibility
set_data_type_real = lambda: set_data_type('real')
set_data_type_synthetic = lambda: set_data_type('synthetic')
