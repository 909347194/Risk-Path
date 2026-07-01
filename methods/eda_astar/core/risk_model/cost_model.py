from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import geopandas as gpd
import numpy as np
import rasterio
from pyproj import Transformer
from shapely.geometry import Polygon

try:
    from .grid_model import Grid3D
except ImportError:
    from grid_model import Grid3D


class IntegratedCostModel:
    """
    Integrated cost assessment model with proper normalization and weighting.
    
    Implements Eq. from Pang et al. (2022):
    c_v = α_1 × ω_1 × c_fatality + α_2 × ω_2 × c_property + α_3 × ω_3 × c_noise
    
    Key features:
    - Weight factors α_τ sum to 1.0
    - Normalization factors ω_τ = 1 / max(c_τ)
    - Separate risk models for each risk type
    """

    def __init__(
        self,
        grid: Grid3D,
        population_raster: Path,
        buildings: gpd.GeoDataFrame,
        # Weight factors (must sum to 1.0)
        alpha_fatality: float = 0.5,      # α_1: fatality risk weight
        alpha_property: float = 0.3,      # α_2: property damage weight  
        alpha_noise: float = 0.2,         # α_3: noise impact weight
        # Other parameters
        clearance: float = 5.0,
        distance_weight: float = 1.0,
        collision_penalty: float = 1e5,
        fatality_decay: float = 40.0,
        noise_decay: float = 60.0,
    ):
        self.grid = grid
        self.population_raster = Path(population_raster)
        self.buildings = buildings.copy()
        self.clearance = float(clearance)
        self.distance_weight = float(distance_weight)
        self.collision_penalty = float(collision_penalty)
        self.fatality_decay = float(fatality_decay)
        self.noise_decay = float(noise_decay)
        
        # Validate weight factors
        self.alpha_fatality = float(alpha_fatality)
        self.alpha_property = float(alpha_property)
        self.alpha_noise = float(alpha_noise)
        
        weight_sum = self.alpha_fatality + self.alpha_property + self.alpha_noise
        if not np.isclose(weight_sum, 1.0):
            raise ValueError(
                f"Weight factors must sum to 1.0, got {weight_sum:.4f}. "
                f"Please adjust: α_fatality={alpha_fatality}, "
                f"α_property={alpha_property}, α_noise={alpha_noise}"
            )
        
        # CRS handling
        if self.buildings.crs is None:
            raise ValueError("Buildings GeoDataFrame must have CRS")
        if self.buildings.crs.to_string() != self.grid.target_crs:
            self.buildings = self.buildings.to_crs(self.grid.target_crs)
        
        if "height" not in self.buildings.columns:
            self.buildings["height"] = 0.0

    def sample_population_density(self) -> np.ndarray:
        """Sample population density from raster file."""
        with rasterio.open(self.population_raster) as src:
            if src.crs is None:
                raise ValueError("Population raster has no CRS")

            transformer = None
            if src.crs.to_string() != self.grid.target_crs:
                transformer = Transformer.from_crs(
                    self.grid.target_crs, src.crs, always_xy=True
                )

            centers = self.grid.centers.reshape(-1, 2)
            if transformer is not None:
                xs, ys = transformer.transform(centers[:, 0], centers[:, 1])
                coords = np.stack([xs, ys], axis=1)
            else:
                coords = centers

            samples = list(src.sample(coords))
            values = np.array(
                [float(row[0]) if row is not None and row[0] is not None else 0.0 
                 for row in samples],
                dtype=float
            )
            values = values.reshape(self.grid.height, self.grid.width)
            values[values < 0] = 0.0
            return values

    def compute_building_stats(self) -> tuple[np.ndarray, np.ndarray]:
        """Compute building height and overlap statistics."""
        heights = np.zeros((self.grid.height, self.grid.width), dtype=float)
        overlap = np.zeros((self.grid.height, self.grid.width), dtype=float)

        if len(self.buildings) == 0:
            return heights, overlap

        spatial_index = self.buildings.sindex
        geometry_values = self.buildings.geometry.values
        height_values = np.asarray(
            self.buildings["height"].fillna(0.0), dtype=float
        )

        polys = self.grid.cell_polygons
        for idx, cell in enumerate(polys):
            row = idx // self.grid.width
            col = idx % self.grid.width
            candidates = list(spatial_index.intersection(cell.bounds))
            if not candidates:
                continue
            max_height = 0.0
            overlap_area = 0.0
            for candidate in candidates:
                candidate_geom = geometry_values[candidate]
                if not candidate_geom.intersects(cell):
                    continue
                intersection = candidate_geom.intersection(cell)
                if intersection.is_empty:
                    continue
                max_height = max(max_height, float(height_values[candidate]))
                overlap_area += float(intersection.area)
            heights[row, col] = max_height
            overlap[row, col] = min(overlap_area / self.grid.cell_area, 1.0)

        return heights, overlap

    def normalize_cost_map(self, cost_map: np.ndarray) -> tuple[np.ndarray, float]:
        """
        Normalize cost map to [0, 1] range.
        
        ω_τ = 1 / c_τ_max
        
        Parameters:
            cost_map: Raw cost array
            
        Returns:
            Tuple of (normalized_cost, max_cost)
        """
        max_cost = float(np.max(cost_map))
        
        if max_cost <= 0:
            # Avoid division by zero
            return np.zeros_like(cost_map), max_cost
        
        # Normalized cost: c_normalized = c / c_max
        normalized_cost = cost_map / max_cost
        
        return normalized_cost, max_cost

    def compute_integrated_costs(self) -> Dict[str, Any]:
        """
        Compute integrated costs using the additive linear model.
        
        For each altitude layer:
        1. Compute raw costs for each risk type
        2. Normalize each cost map: ω_τ = 1 / max(c_τ)
        3. Apply weighted combination: c_v = Σ α_τ × ω_τ × c_τ
        
        Returns:
            Dictionary containing:
            - 'raw_costs': Dict of raw cost maps by type and layer
            - 'normalized_costs': Dict of normalized cost maps
            - 'integrated_costs': Final integrated cost maps
            - 'normalization_factors': ω_τ values
            - 'max_costs': c_τ_max values
        """
        # Sample data
        population = self.sample_population_density()
        building_heights, overlap_ratio = self.compute_building_stats()
        
        # Storage for results
        results = {
            'raw_costs': {
                'fatality': [],
                'property': [],
                'noise': [],
            },
            'normalized_costs': {
                'fatality': [],
                'property': [],
                'noise': [],
            },
            'integrated_costs': [],
            'collision_costs': [],
            'normalization_factors': {
                'fatality': [],
                'property': [],
                'noise': [],
            },
            'max_costs': {
                'fatality': [],
                'property': [],
                'noise': [],
            },
        }
        
        # Process each altitude layer
        for altitude in self.grid.layer_altitudes:
            
            # ===== Step 1: Compute raw costs for each risk type =====
            
            # Fatality risk: population * (1.0 + exp(-altitude / decay))
            fatality_raw = population * (1.0 + np.exp(-altitude / self.fatality_decay))
            
            # Property damage risk: overlap_ratio * (building_heights / 100.0)
            property_raw = overlap_ratio * (building_heights / 100.0)
            
            # Noise impact risk: population * exp(-altitude / decay)
            noise_raw = population * np.exp(-altitude / self.noise_decay)
            
            # Collision penalty
            collision = np.where(
                building_heights + self.clearance >= altitude,
                self.collision_penalty,
                0.0
            )
            
            # Store raw costs
            results['raw_costs']['fatality'].append(fatality_raw)
            results['raw_costs']['property'].append(property_raw)
            results['raw_costs']['noise'].append(noise_raw)
            results['collision_costs'].append(collision)
            
            # ===== Step 2: Normalize each cost map =====
            
            fatality_norm, fatality_max = self.normalize_cost_map(fatality_raw)
            property_norm, property_max = self.normalize_cost_map(property_raw)
            noise_norm, noise_max = self.normalize_cost_map(noise_raw)
            
            # Normalization factors: ω_τ = 1 / c_τ_max
            omega_fatality = 1.0 / fatality_max if fatality_max > 0 else 0.0
            omega_property = 1.0 / property_max if property_max > 0 else 0.0
            omega_noise = 1.0 / noise_max if noise_max > 0 else 0.0
            
            # Store normalized costs and factors
            results['normalized_costs']['fatality'].append(fatality_norm)
            results['normalized_costs']['property'].append(property_norm)
            results['normalized_costs']['noise'].append(noise_norm)
            results['normalization_factors']['fatality'].append(omega_fatality)
            results['normalization_factors']['property'].append(omega_property)
            results['normalization_factors']['noise'].append(omega_noise)
            results['max_costs']['fatality'].append(fatality_max)
            results['max_costs']['property'].append(property_max)
            results['max_costs']['noise'].append(noise_max)
            
            # ===== Step 3: Apply weighted combination =====
            # c_v = α_1 × ω_1 × c_1 + α_2 × ω_2 × c_2 + α_3 × ω_3 × c_3
            
            integrated_cost = (
                self.alpha_fatality * omega_fatality * fatality_raw +
                self.alpha_property * omega_property * property_raw +
                self.alpha_noise * omega_noise * noise_raw
            )
            
            # Add distance weight and collision penalty
            total_cost = self.distance_weight + integrated_cost + collision
            
            results['integrated_costs'].append(total_cost)
        
        # Stack arrays for all layers
        for key in ['fatality', 'property', 'noise']:
            results['raw_costs'][key] = np.stack(
                results['raw_costs'][key], axis=0
            )
            results['normalized_costs'][key] = np.stack(
                results['normalized_costs'][key], axis=0
            )
            results['normalization_factors'][key] = np.array(
                results['normalization_factors'][key]
            )
            results['max_costs'][key] = np.array(
                results['max_costs'][key]
            )
        
        results['integrated_costs'] = np.stack(
            results['integrated_costs'], axis=0
        )
        results['collision_costs'] = np.stack(
            results['collision_costs'], axis=0
        )
        
        return results

    def save_cost_maps(
        self, 
        results: Dict[str, Any], 
        output_file: Path
    ) -> None:
        """Save all cost maps to compressed NPZ file."""
        output_file = Path(output_file)
        
        save_dict = {
            # Integrated costs
            'integrated_costs': results['integrated_costs'],
            'collision_costs': results['collision_costs'],
            
            # Raw costs
            'fatality_raw': results['raw_costs']['fatality'],
            'property_raw': results['raw_costs']['property'],
            'noise_raw': results['raw_costs']['noise'],
            
            # Normalized costs
            'fatality_normalized': results['normalized_costs']['fatality'],
            'property_normalized': results['normalized_costs']['property'],
            'noise_normalized': results['normalized_costs']['noise'],
            
            # Normalization factors and max values
            'omega_fatality': results['normalization_factors']['fatality'],
            'omega_property': results['normalization_factors']['property'],
            'omega_noise': results['normalization_factors']['noise'],
            'max_fatality': results['max_costs']['fatality'],
            'max_property': results['max_costs']['property'],
            'max_noise': results['max_costs']['noise'],
            
            # Metadata
            'layer_altitudes': self.grid.layer_altitudes,
            'alpha_fatality': np.array([self.alpha_fatality]),
            'alpha_property': np.array([self.alpha_property]),
            'alpha_noise': np.array([self.alpha_noise]),
        }
        
        np.savez_compressed(output_file, **save_dict)

    def summary(self, results: Dict[str, Any]) -> str:
        """Generate summary statistics for integrated costs."""
        lines = []
        lines.append("=" * 70)
        lines.append("Integrated Cost Model Summary")
        lines.append("=" * 70)
        
        lines.append(f"\nWeight Factors (α_τ):")
        lines.append(f"  α_fatality = {self.alpha_fatality:.2f}")
        lines.append(f"  α_property = {self.alpha_property:.2f}")
        lines.append(f"  α_noise    = {self.alpha_noise:.2f}")
        lines.append(f"  Sum        = {self.alpha_fatality + self.alpha_property + self.alpha_noise:.4f}")
        
        lines.append(f"\nNormalization Factors (ω_τ) by Layer:")
        for layer_idx, altitude in enumerate(self.grid.layer_altitudes):
            lines.append(f"\n  Layer {layer_idx} ({altitude:.0f}m):")
            lines.append(f"    ω_fatality = {results['normalization_factors']['fatality'][layer_idx]:.6f}")
            lines.append(f"    ω_property = {results['normalization_factors']['property'][layer_idx]:.6f}")
            lines.append(f"    ω_noise    = {results['normalization_factors']['noise'][layer_idx]:.6f}")
        
        lines.append(f"\nIntegrated Cost Statistics by Layer:")
        total = results['integrated_costs']
        for layer_idx, altitude in enumerate(self.grid.layer_altitudes):
            arr = total[layer_idx]
            blocked = np.count_nonzero(arr >= self.collision_penalty)
            lines.append(
                f"  Layer {layer_idx} ({altitude:.0f}m): "
                f"min={arr.min():.2f}, mean={arr.mean():.2f}, "
                f"max={arr.max():.2f}, blocked={blocked}"
            )
        
        lines.append("=" * 70)
        return "\n".join(lines)


# Backward compatibility alias
RiskCostModel = IntegratedCostModel
