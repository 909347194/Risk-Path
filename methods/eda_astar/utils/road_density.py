"""
Road Density Calculator for Traffic Risk Assessment

This module calculates traffic density based on road network data using a Gaussian
decay model (Eq. 12 from the paper).

Usage:
    from utils.road_density import calculate_traffic_density
    
    density_map, metadata = calculate_traffic_density(
        grid_size=80,
        radius=1.0,
        sigma_v_avg=7120
    )
"""

import numpy as np
import geopandas as gpd
from scipy.spatial import KDTree
from pathlib import Path
from typing import Tuple, Dict, Optional


def load_boundary_data() -> gpd.GeoDataFrame:
    """Load study area boundary from GeoJSON file.
    
    Returns:
        GeoDataFrame with boundary geometry in EPSG:3857 projection
    """
    boundary_file = Path(__file__).parent.parent / "data" / "buildings_max_range.geojson"
    boundary_gdf = gpd.read_file(boundary_file)
    
    print(f"✓ Loaded boundary file: {boundary_file}")
    print(f"  Original CRS: {boundary_gdf.crs}")
    
    # Convert to projected coordinate system (meters)
    boundary_gdf = boundary_gdf.to_crs("EPSG:3857")
    
    return boundary_gdf


def extract_hot_points(
    road_dir: Optional[Path] = None,
    highway_types: list = ['motorway', 'trunk', 'primary']
) -> np.ndarray:
    """Extract attraction points from road network data.
    
    Args:
        road_dir: Directory containing road shapefiles. If None, uses default path.
        highway_types: List of highway types to filter (if 'highway' column exists)
        
    Returns:
        Array of hot point coordinates (x, y) in EPSG:3857
    """
    if road_dir is None:
        road_dir = Path(__file__).parent.parent / "data" / "road"
    
    road_files = list(road_dir.glob("*.shp"))
    
    if not road_files:
        raise ValueError(f"No road data found at: {road_dir}")
    
    # Use first shapefile
    road_file = road_files[0]
    print(f"✓ Loaded road data: {road_file.name}")
    roads = gpd.read_file(road_file)
    
    # Ensure consistent CRS
    if roads.crs is None:
        roads.crs = "EPSG:4326"  # Assume WGS84
    roads = roads.to_crs("EPSG:3857")
    
    # Filter high-grade roads
    if 'highway' in roads.columns:
        hot_roads = roads[roads['highway'].isin(highway_types)]
        print(f"  Filtered high-grade roads: {len(hot_roads)} (from {len(roads)})")
    else:
        hot_roads = roads
        print(f"  Using all roads: {len(hot_roads)}")
    
    # Extract road endpoints as attraction points
    hot_points = []
    for idx, row in hot_roads.iterrows():
        geom = row.geometry
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            if len(coords) >= 2:
                hot_points.append(coords[0])
                hot_points.append(coords[-1])
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                coords = list(line.coords)
                if len(coords) >= 2:
                    hot_points.append(coords[0])
                    hot_points.append(coords[-1])
    
    hot_points_array = np.array(hot_points)
    print(f"  Extracted {len(hot_points_array)} attraction points")
    
    return hot_points_array


def compute_study_area_bounds(
    boundary_gdf: gpd.GeoDataFrame,
    padding: float = 500
) -> Tuple[float, float, float, float]:
    """Compute study area bounds with padding.
    
    Args:
        boundary_gdf: Boundary GeoDataFrame in EPSG:3857
        padding: Padding in meters
        
    Returns:
        Tuple of (x_min, y_min, x_max, y_max)
    """
    bounds = boundary_gdf.total_bounds
    
    x_min = bounds[0] - padding
    y_min = bounds[1] - padding
    x_max = bounds[2] + padding
    y_max = bounds[3] + padding
    
    print(f"\n✓ Study area bounds (with {padding}m padding):")
    print(f"  X: {x_min:.0f} to {x_max:.0f} (width: {x_max - x_min:.0f}m)")
    print(f"  Y: {y_min:.0f} to {y_max:.0f} (height: {y_max - y_min:.0f}m)")
    print(f"  Area: {(x_max-x_min)*(y_max-y_min)/1e6:.2f} km²")
    
    return x_min, y_min, x_max, y_max


def calculate_traffic_density(
    grid_size: float = 80.0,
    radius: float = 1.0,
    sigma_v_avg: float = 7120.0,
    hot_points: Optional[np.ndarray] = None,
    bounds: Optional[Tuple[float, float, float, float]] = None,
    verbose: bool = True
) -> Tuple[Dict[Tuple[float, float], float], dict]:
    """Calculate traffic density map using Gaussian decay model (Eq. 12).
    
    Formula: σ_v(r) = exp(1 - r²) × σ_v_avg, where r = distance / 1000 (km)
    
    Args:
        grid_size: Grid cell size in meters (default: 80m)
        radius: Attraction radius in km (default: 1.0 km)
        sigma_v_avg: Average traffic density parameter
        hot_points: Pre-computed attraction points. If None, loads from road data.
        bounds: Study area bounds (x_min, y_min, x_max, y_max). If None, computes from boundary.
        verbose: Print progress information
        
    Returns:
        Tuple of (density_map, metadata)
        - density_map: Dict mapping (x, y) coordinates to density values
        - metadata: Dictionary with computation parameters
    """
    # Load or use provided data
    if hot_points is None:
        hot_points = extract_hot_points()
    
    if bounds is None:
        boundary_gdf = load_boundary_data()
        bounds = compute_study_area_bounds(boundary_gdf)
    
    x_min, y_min, x_max, y_max = bounds
    
    # Build KDTree for nearest neighbor search
    tree = KDTree(hot_points)
    if verbose:
        print(f"\n✓ KDTree built with {len(hot_points)} points")
    
    # Generate grid coordinates
    x_coords = np.arange(x_min, x_max, grid_size)
    y_coords = np.arange(y_min, y_max, grid_size)
    
    if verbose:
        print(f"\n✓ Computing traffic density:")
        print(f"  Grid size: {grid_size}m")
        print(f"  Grid cells: {len(x_coords)} x {len(y_coords)} = {len(x_coords) * len(y_coords)}")
    
    # Calculate density for each grid cell
    density_map = {}
    total_cells = len(x_coords) * len(y_coords)
    processed = 0
    
    for i, x in enumerate(x_coords):
        for j, y in enumerate(y_coords):
            # Find nearest attraction point distance (convert to km)
            dist, _ = tree.query([x, y])
            r = dist / 1000.0
            
            # Gaussian decay model (Eq. 12)
            if r > radius:
                r = radius
            sigma_v = np.exp(1 - r**2) * sigma_v_avg
            
            # Store density
            density_map[(x, y)] = sigma_v
            processed += 1
            
            # Progress reporting
            if verbose and (processed % 1000 == 0 or processed == total_cells):
                print(f"  Progress: {processed}/{total_cells} ({processed/total_cells*100:.1f}%)")
    
    if verbose:
        print(f"\n✓ Traffic density calculation complete!")
        print(f"  Total cells: {len(density_map)}")
        print(f"  Density range: {min(density_map.values()):.2f} ~ {max(density_map.values()):.2f}")
    
    # Prepare metadata
    metadata = {
        'x_min': x_min,
        'y_min': y_min,
        'x_max': x_max,
        'y_max': y_max,
        'grid_size': grid_size,
        'radius': radius,
        'sigma_v_avg': sigma_v_avg,
        'x_coords': x_coords,
        'y_coords': y_coords,
        'num_hot_points': len(hot_points),
    }
    
    return density_map, metadata


def save_density_to_numpy(
    density_map: Dict[Tuple[float, float], float],
    metadata: dict,
    output_dir: Optional[Path] = None
) -> Path:
    """Save traffic density map to NumPy files.
    
    Args:
        density_map: Density map dictionary
        metadata: Computation metadata
        output_dir: Output directory. If None, uses data directory.
        
    Returns:
        Path to saved .npy file
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Convert density map to 2D array
    x_coords = metadata['x_coords']
    y_coords = metadata['y_coords']
    density_array = np.array([
        [density_map.get((x, y), 0) for y in y_coords]
        for x in x_coords
    ])
    
    # Save density array
    output_file = output_dir / "traffic_density.npy"
    np.save(output_file, density_array)
    print(f"✓ Saved density array to: {output_file}")
    
    # Save metadata
    metadata_file = output_dir / "traffic_density_metadata.npz"
    np.savez(metadata_file, **metadata)
    print(f"✓ Saved metadata to: {metadata_file}")
    
    return output_file


# ===================== Main execution (for standalone testing) =====================
if __name__ == "__main__":
    print("=" * 80)
    print("Traffic Density Calculator - Standalone Mode")
    print("=" * 80)
    
    # Calculate traffic density
    density_map, metadata = calculate_traffic_density(
        grid_size=80,
        radius=1.0,
        sigma_v_avg=7120,
        verbose=True
    )
    
    # Save to NumPy files
    output_file = save_density_to_numpy(density_map, metadata)
    
    print("\n" + "=" * 80)
    print("✓ Traffic density calculation complete!")
    print("=" * 80)