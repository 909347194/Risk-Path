"""
3D Path Graph for UAV Navigation

Implements the graph structure for 3D airspace path planning.
Nodes represent grid cell centroids at different altitude layers.
Edges connect neighboring cells with transition costs.
"""

from __future__ import annotations

import numpy as np
from typing import Iterable

try:
    from .grid_model import Grid3D
except ImportError:
    try:
        from core.risk_model.grid_model import Grid3D
    except ImportError:
        from src.EDAcostAstar.risk_model.grid_model import Grid3D


class Grid3DPathGraph:
    """3D UAV path graph over a layer-based airspace grid.
    
    This class builds a graph where:
    - Nodes: Centroid points of 80m x 80m air blocks at each flight layer
    - Edges: 26-connectivity (3x3x3 neighborhood excluding self)
    
    The graph supports path planning algorithms like A* and EDA-CostA*.
    """

    # 26 directional offsets for 3D neighborhood (excluding self)
    OFFSETS = np.array(
        [
            (dl, dr, dc)
            for dl in (-1, 0, 1)
            for dr in (-1, 0, 1)
            for dc in (-1, 0, 1)
            if not (dl == 0 and dr == 0 and dc == 0)
        ],
        dtype=int,
    )

    def __init__(
        self,
        grid: Grid3D,
        safe_separation: float = 40.0,
        vertical_transition_cost: float = 1.5,
    ):
        """
        Args:
            grid: 3D airspace grid
            safe_separation: Minimum distance between waypoints (meters)
            vertical_transition_cost: Cost multiplier for altitude changes
        """
        self.grid = grid
        self.safe_separation = float(safe_separation)
        self.vertical_transition_cost = float(vertical_transition_cost)
        self.layer_count = len(grid.layer_altitudes)
        self.node_count = self.layer_count * grid.height * grid.width

    # ========== Node Indexing ==========
    
    def is_within_bounds(self, layer: int, row: int, col: int) -> bool:
        """Check if grid coordinates are within valid range."""
        return (
            0 <= layer < self.layer_count
            and 0 <= row < self.grid.height
            and 0 <= col < self.grid.width
        )

    def index(self, layer: int, row: int, col: int) -> int:
        """Convert 3D coordinates to linear node index.
        
        Formula: index = layer * (height * width) + row * width + col
        """
        return layer * (self.grid.height * self.grid.width) + row * self.grid.width + col

    def unpack_index(self, node_index: int) -> tuple[int, int, int]:
        """Convert linear node index back to 3D coordinates.
        
        Returns:
            (layer, row, col) tuple
        """
        layer_size = self.grid.height * self.grid.width
        layer = node_index // layer_size
        remainder = node_index % layer_size
        row = remainder // self.grid.width
        col = remainder % self.grid.width
        return layer, row, col

    # ========== Spatial Operations ==========
    
    def centroid(self, layer: int, row: int, col: int) -> np.ndarray:
        """Get 3D coordinates (x, y, z) of a grid cell centroid.
        
        Args:
            layer: Altitude layer index
            row: Row index in grid
            col: Column index in grid
            
        Returns:
            numpy array [x, y, z] where z is altitude
        """
        x, y = self.grid.centers[row, col]
        z = self.grid.layer_altitudes[layer]
        return np.array([x, y, z], dtype=float)

    def neighbor_indices(self, layer: int, row: int, col: int) -> list[int]:
        """Get all valid neighboring node indices (26-connectivity).
        
        Args:
            layer: Current layer
            row: Current row
            col: Current column
            
        Returns:
            List of neighbor node indices
        """
        neighbors: list[int] = []
        for dl, dr, dc in self.OFFSETS:
            candidate = (layer + dl, row + dr, col + dc)
            if self.is_within_bounds(*candidate):
                neighbors.append(self.index(*candidate))
        return neighbors

    # ========== Edge Cost Computation ==========
    
    def transition_vector(self, from_index: int, to_index: int) -> np.ndarray:
        """Compute 3D vector between two nodes."""
        from_layer, from_row, from_col = self.unpack_index(from_index)
        to_layer, to_row, to_col = self.unpack_index(to_index)
        return self.centroid(to_layer, to_row, to_col) - self.centroid(from_layer, from_row, from_col)

    def transition_distance(self, from_index: int, to_index: int) -> float:
        """Compute Euclidean distance between two nodes."""
        return float(np.linalg.norm(self.transition_vector(from_index, to_index)))

    def is_safe_transition(self, from_index: int, to_index: int) -> bool:
        """Check if transition meets minimum separation requirement."""
        distance = self.transition_distance(from_index, to_index)
        return distance >= self.safe_separation

    def transition_cost(
        self,
        from_index: int,
        to_index: int,
        cost_map: np.ndarray | None = None,
        risk_weight: float = 1.0,
        distance_weight: float = 1.0,
    ) -> float:
        """Compute total cost for transitioning between two nodes.
        
        Cost = distance_weight * distance + risk_weight * vertex_cost + vertical_cost
        
        Args:
            from_index: Source node index
            to_index: Destination node index
            cost_map: 3D array of vertex costs (layer, row, col)
            risk_weight: Weight for risk/cost component
            distance_weight: Weight for distance component
            
        Returns:
            Total transition cost (inf if unsafe)
        """
        # Base distance cost
        distance = self.transition_distance(from_index, to_index)
        if not self.is_safe_transition(from_index, to_index):
            return float("inf")

        # Vertex cost at destination
        if cost_map is None:
            map_cost = 0.0
        else:
            layer, row, col = self.unpack_index(to_index)
            map_cost = float(cost_map[layer, row, col])

        # Vertical transition penalty
        from_layer, _, _ = self.unpack_index(from_index)
        to_layer, _, _ = self.unpack_index(to_index)
        vertical_cost = (
            self.vertical_transition_cost * 
            abs(self.grid.layer_altitudes[to_layer] - self.grid.layer_altitudes[from_layer]) / 30.0
        )

        return distance_weight * distance + risk_weight * map_cost + vertical_cost

    # ========== Path Utilities ==========
    
    def node_centroid_sequence(self, path: Iterable[int]) -> np.ndarray:
        """Convert path of node indices to 3D coordinates.
        
        Args:
            path: List of node indices
            
        Returns:
            numpy array of shape (N, 3) with [x, y, z] coordinates
        """
        return np.vstack([self.centroid(*self.unpack_index(node)) for node in path])

    def find_neighbors_and_costs(
        self,
        layer: int,
        row: int,
        col: int,
        cost_map: np.ndarray | None = None,
        risk_weight: float = 1.0,
        distance_weight: float = 1.0,
    ) -> list[tuple[int, float]]:
        """Get valid neighbors with their transition costs.
        
        Args:
            layer: Current layer
            row: Current row
            col: Current column
            cost_map: 3D cost array
            risk_weight: Risk weight
            distance_weight: Distance weight
            
        Returns:
            List of (neighbor_index, cost) tuples
        """
        node = self.index(layer, row, col)
        neighbor_costs: list[tuple[int, float]] = []
        for neighbor in self.neighbor_indices(layer, row, col):
            cost = self.transition_cost(
                node, neighbor, 
                cost_map=cost_map, 
                risk_weight=risk_weight, 
                distance_weight=distance_weight
            )
            if cost < float("inf"):
                neighbor_costs.append((neighbor, cost))
        return neighbor_costs
