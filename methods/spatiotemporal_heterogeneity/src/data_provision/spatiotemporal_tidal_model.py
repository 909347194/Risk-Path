"""
Spatiotemporal tidal models for population and traffic density.

Data-provision responsibility:
    base_pop_2d.npy + poi_counts.npz -> dynamic 2D time series

This module deliberately stops at aligned NumPy matrices. It does not create
4D risk/cost tensors; height broadcasting and cost fusion belong to
src/tensor_engine.

Supports both synthetic and real data with automatic path switching:

    Synthetic: data/02_processed/synthetic/rho_pop_3d.npy
               data/02_processed/synthetic/rho_vehicle_3d.npy
    Real:      data/02_processed/rho_pop_3d.npy
               data/02_processed/rho_vehicle_3d.npy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple, Union

import numpy as np

try:
    from ..tensor_engine.grid_system import GridSystem, get_micro_grid
    from .poi_parser import POI_CATEGORIES, load_poi_counts
    from .population_resampler import load_base_population
    from .paths import DataPaths, get_data_paths, get_data_type
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tensor_engine.grid_system import GridSystem, get_micro_grid
    from data_provision.poi_parser import POI_CATEGORIES, load_poi_counts
    from data_provision.population_resampler import load_base_population
    from data_provision.paths import DataPaths, get_data_paths, get_data_type


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "02_processed"
DEFAULT_RHO_POP_PATH = DEFAULT_PROCESSED_DIR / "rho_pop_3d.npy"
DEFAULT_RHO_VEHICLE_PATH = DEFAULT_PROCESSED_DIR / "rho_vehicle_3d.npy"


@dataclass
class TidalModelConfig:
    """Parameters for the POI tidal gravity model."""

    population_weights: Dict[str, float] = field(default_factory=lambda: {
        "residential": 1.0,
        "office": 1.2,
        "institution": 1.5,
        "transport": 1.8,
        "industrial": 0.3,
    })
    population_sigma_m: Dict[str, float] = field(default_factory=lambda: {
        "residential": 400.0,
        "office": 350.0,
        "institution": 300.0,
        "transport": 250.0,
        "industrial": 500.0,
    })
    traffic_weights: Dict[str, float] = field(default_factory=lambda: {
        "residential": 1.0,
        "office": 1.5,
        "institution": 0.8,
        "transport": 2.0,
        "industrial": 0.6,
    })
    traffic_sigma_m: Dict[str, float] = field(default_factory=lambda: {
        "residential": 220.0,
        "office": 220.0,
        "institution": 180.0,
        "transport": 160.0,
        "industrial": 250.0,
    })
    population_background: float = 0.10
    traffic_background: float = 0.05


class SpatiotemporalTidalModel:
    """
    Common implementation for POI-driven tidal density models.

    Formula used in engineering form:

        rho(i,t) = rho_base(i) * [b + sum_k W_k * tau_k(t) * A_k(i)]

    where A_k(i) is a normalized Gaussian influence map generated from POI
    count rasters. The small background term b keeps a non-zero baseline in
    places where POI coverage is sparse.
    """

    def __init__(
        self,
        grid: Optional[GridSystem] = None,
        config: Optional[TidalModelConfig] = None,
    ):
        self.grid = grid or get_micro_grid()
        self.config = config or TidalModelConfig()

    def build_population_density(
        self,
        base_population: np.ndarray,
        poi_counts: Mapping[str, np.ndarray],
        *,
        normalize: bool = False,
        save_path: Optional[Union[str, Path]] = None,
    ) -> np.ndarray:
        """Build dynamic population density rho_pop[x, y, t]."""

        rho = self._build_density(
            base_map=base_population,
            poi_counts=poi_counts,
            weights=self.config.population_weights,
            sigma_m=self.config.population_sigma_m,
            background=self.config.population_background,
            profile_fn=population_activation,
        )
        if normalize:
            rho = _minmax_normalize(rho)
        if save_path is not None:
            save_density(rho, save_path)
        return rho

    def build_vehicle_density(
        self,
        base_vehicle: np.ndarray,
        poi_counts: Mapping[str, np.ndarray],
        *,
        normalize: bool = False,
        save_path: Optional[Union[str, Path]] = None,
    ) -> np.ndarray:
        """Build dynamic traffic/vehicle density rho_vehicle[x, y, t]."""

        rho = self._build_density(
            base_map=base_vehicle,
            poi_counts=poi_counts,
            weights=self.config.traffic_weights,
            sigma_m=self.config.traffic_sigma_m,
            background=self.config.traffic_background,
            profile_fn=traffic_activation,
        )
        if normalize:
            rho = _minmax_normalize(rho)
        if save_path is not None:
            save_density(rho, save_path)
        return rho

    def _build_density(
        self,
        *,
        base_map: np.ndarray,
        poi_counts: Mapping[str, np.ndarray],
        weights: Mapping[str, float],
        sigma_m: Mapping[str, float],
        background: float,
        profile_fn,
    ) -> np.ndarray:
        base_map = np.asarray(base_map, dtype=np.float64)
        self._validate_xy(base_map, "base_map")

        nt = self.grid.temporal.nt
        density = np.zeros((self.grid.spatial.nx, self.grid.spatial.ny, nt), dtype=np.float64)
        influence_maps = self._build_influence_maps(poi_counts, sigma_m)

        for t_idx, hour in enumerate(np.mod(self.grid.time_hours, 24.0)):
            multiplier = np.full(base_map.shape, float(background), dtype=np.float64)
            for category in POI_CATEGORIES:
                tau = profile_fn(category, float(hour))
                multiplier += weights.get(category, 0.0) * tau * influence_maps[category]
            density[:, :, t_idx] = base_map * multiplier

        density = np.nan_to_num(density, nan=0.0, posinf=0.0, neginf=0.0)
        density[density < 0] = 0.0
        return density.astype(np.float32)

    def _build_influence_maps(
        self,
        poi_counts: Mapping[str, np.ndarray],
        sigma_m: Mapping[str, float],
    ) -> Dict[str, np.ndarray]:
        influence_maps: Dict[str, np.ndarray] = {}

        for category in POI_CATEGORIES:
            counts = np.asarray(poi_counts.get(category, np.zeros(self._xy_shape)), dtype=np.float64)
            self._validate_xy(counts, f"poi_counts[{category}]")
            sigma_cells = max(float(sigma_m.get(category, 300.0)) / self.grid.spatial.dx, 1e-6)
            influence = _gaussian_smooth(counts, sigma_cells)
            max_value = float(influence.max())
            if max_value > 0:
                influence = influence / max_value
            influence_maps[category] = influence

        return influence_maps

    @property
    def _xy_shape(self) -> Tuple[int, int]:
        return (self.grid.spatial.nx, self.grid.spatial.ny)

    def _validate_xy(self, array: np.ndarray, name: str):
        if array.shape != self._xy_shape:
            raise ValueError(f"{name} must have shape {self._xy_shape}, got {array.shape}.")


class SpatiotemporalTidalModelforPopulationDensity(SpatiotemporalTidalModel):
    """Backward-compatible class name for population density modeling."""

    def build(
        self,
        base_population: np.ndarray,
        poi_counts: Mapping[str, np.ndarray],
        **kwargs,
    ) -> np.ndarray:
        return self.build_population_density(base_population, poi_counts, **kwargs)


class SpatiotemporalTidalModelforTrafficDensity(SpatiotemporalTidalModel):
    """Backward-compatible class name for traffic density modeling."""

    def build(
        self,
        base_vehicle: np.ndarray,
        poi_counts: Mapping[str, np.ndarray],
        **kwargs,
    ) -> np.ndarray:
        return self.build_vehicle_density(base_vehicle, poi_counts, **kwargs)


def population_activation(category: str, hour: float) -> float:
    """Empirical 24h activation profile for population density."""

    if category == "residential":
        night = _night_window(hour, start=18.0, end=7.0)
        commute = 0.35 * (_gaussian(hour, 8.0, 1.0) + _gaussian(hour, 18.5, 1.2))
        return float(np.clip(0.25 + 0.75 * night + commute, 0.0, 1.0))

    if category == "office":
        work_plateau = 0.85 if 9.0 <= hour < 17.5 else 0.08
        peaks = 0.25 * (_gaussian(hour, 8.5, 0.8) + _gaussian(hour, 18.0, 1.0))
        return float(np.clip(work_plateau + peaks, 0.0, 1.0))

    if category == "institution":
        if 8.0 <= hour < 17.0:
            return float(np.clip(0.75 + 0.25 * _gaussian(hour, 12.5, 3.0), 0.0, 1.0))
        return 0.05

    if category == "transport":
        return float(np.clip(
            0.20 + 0.80 * _gaussian(hour, 8.25, 0.65) + 0.80 * _gaussian(hour, 18.25, 0.75),
            0.0,
            1.0,
        ))

    if category == "industrial":
        if 8.0 <= hour < 18.0:
            return 0.35
        return 0.12

    return 0.0


def traffic_activation(category: str, hour: float) -> float:
    """Empirical 24h activation profile for vehicle density."""

    if category == "transport":
        return float(np.clip(
            0.20 + 0.85 * _gaussian(hour, 8.5, 0.55) + 0.85 * _gaussian(hour, 18.5, 0.65),
            0.0,
            1.0,
        ))

    if category == "office":
        plateau = 0.70 if 9.5 <= hour < 17.5 else 0.20
        peaks = 0.25 * (_gaussian(hour, 8.5, 0.8) + _gaussian(hour, 18.2, 0.8))
        return float(np.clip(plateau + peaks, 0.0, 1.0))

    if category == "residential":
        peaks = 0.35 * (_gaussian(hour, 7.8, 0.9) + _gaussian(hour, 18.5, 1.0))
        night_base = 0.35 if hour >= 19.0 or hour < 7.0 else 0.22
        return float(np.clip(night_base + peaks, 0.0, 1.0))

    if category == "institution":
        return 0.65 if 8.0 <= hour < 17.0 else 0.12

    if category == "industrial":
        return 0.45 if 7.0 <= hour < 19.0 else 0.22

    return 0.0


def build_dynamic_population_density(
    base_pop_path: Optional[Union[str, Path]] = None,
    poi_counts_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
    grid: Optional[GridSystem] = None,
    paths: Optional[DataPaths] = None,
) -> np.ndarray:
    """Load processed inputs and save rho_pop[x, y, t]."""

    grid = grid or get_micro_grid()
    paths = paths or get_data_paths()

    base_pop = load_base_population(
        base_pop_path or paths.base_pop_path,
        paths=paths,
    )
    poi_counts = load_poi_counts(
        poi_counts_path or paths.poi_counts_path,
        paths=paths,
    )
    out = output_path or paths.rho_pop_path
    model = SpatiotemporalTidalModel(grid=grid)
    return model.build_population_density(base_pop, poi_counts, save_path=out)


def build_dynamic_vehicle_density(
    base_vehicle: np.ndarray,
    poi_counts_path: Optional[Union[str, Path]] = None,
    output_path: Optional[Union[str, Path]] = None,
    grid: Optional[GridSystem] = None,
    paths: Optional[DataPaths] = None,
) -> np.ndarray:
    """Build and save rho_vehicle[x, y, t] from a base vehicle map."""

    grid = grid or get_micro_grid()
    paths = paths or get_data_paths()

    poi_counts = load_poi_counts(
        poi_counts_path or paths.poi_counts_path,
        paths=paths,
    )
    out = output_path or paths.rho_vehicle_path
    model = SpatiotemporalTidalModel(grid=grid)
    return model.build_vehicle_density(base_vehicle, poi_counts, save_path=out)


def save_density(
    density: np.ndarray,
    output_path: Optional[Union[str, Path]] = None,
    paths: Optional[DataPaths] = None,
) -> Path:
    """Save density array to the appropriate path."""
    if output_path is None:
        paths = paths or get_data_paths()
        output_path = paths.processed
    output_path = Path(output_path)
    if output_path.suffix == '':
        output_path = output_path / "density.npy"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, np.asarray(density, dtype=np.float32))
    return output_path


def _gaussian(hour: float, mean: float, sigma: float) -> float:
    return float(np.exp(-0.5 * ((hour - mean) / sigma) ** 2))


def _night_window(hour: float, start: float, end: float) -> float:
    return 1.0 if hour >= start or hour < end else 0.0


def _gaussian_smooth(array: np.ndarray, sigma_cells: float) -> np.ndarray:
    try:
        from scipy.ndimage import gaussian_filter

        return gaussian_filter(array, sigma=sigma_cells, mode="nearest")
    except ImportError:
        return _slow_gaussian_smooth(array, sigma_cells)


def _slow_gaussian_smooth(array: np.ndarray, sigma_cells: float) -> np.ndarray:
    """Small fallback used only when scipy is unavailable."""

    radius = max(1, int(3 * sigma_cells))
    x = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (x / sigma_cells) ** 2)
    kernel = kernel / kernel.sum()

    padded_x = np.pad(array, ((radius, radius), (0, 0)), mode="edge")
    temp = np.zeros_like(array, dtype=np.float64)
    for i in range(array.shape[0]):
        temp[i, :] = np.sum(padded_x[i:i + 2 * radius + 1, :] * kernel[:, None], axis=0)

    padded_y = np.pad(temp, ((0, 0), (radius, radius)), mode="edge")
    result = np.zeros_like(array, dtype=np.float64)
    for j in range(array.shape[1]):
        result[:, j] = np.sum(padded_y[:, j:j + 2 * radius + 1] * kernel[None, :], axis=1)
    return result


def _minmax_normalize(array: np.ndarray) -> np.ndarray:
    min_value = float(array.min())
    max_value = float(array.max())
    if max_value <= min_value:
        return np.zeros_like(array, dtype=np.float32)
    return ((array - min_value) / (max_value - min_value)).astype(np.float32)


if __name__ == "__main__":
    from data_provision.poi_parser import create_synthetic_poi_counts
    from data_provision.population_resampler import create_synthetic_base_population

    grid = get_micro_grid()
    base_pop = create_synthetic_base_population(grid=grid, save=False)
    poi_counts = create_synthetic_poi_counts(grid=grid, save=False)
    model = SpatiotemporalTidalModel(grid=grid)
    rho_pop = model.build_population_density(base_pop, poi_counts)
    print(f"rho_pop shape: {rho_pop.shape}")
    print(f"rho_pop range: [{rho_pop.min():.3f}, {rho_pop.max():.3f}]")
