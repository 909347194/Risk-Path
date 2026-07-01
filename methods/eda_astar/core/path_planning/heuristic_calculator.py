"""
Advanced Heuristic Functions for Enhanced Cost A*

Implements the heuristic functions from Pang et al. (2022):
- Eq. 24: Global heuristic distance (h_Dist)
- Eq. 25: Local heuristic direction (h_Drctn)

These heuristics use cluster centroids and cost statistics to provide
more informed guidance than simple Euclidean distance.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Set, Tuple

try:
    from .graph import Grid3DPathGraph
    from .clustering import KMeansClusterer
except ImportError:
    from graph import Grid3DPathGraph
    from clustering import KMeansClusterer


class AdvancedHeuristicCalculator:
    """
    Calculator for advanced heuristic functions (Eq. 24-25).
    
    Computes:
    - h_Dist: Global heuristic based on mean cost statistics
    - h_Drctn: Local heuristic based on distance to nearest centroid
    """
    
    def __init__(
        self,
        graph: Grid3DPathGraph,
        clusterer: KMeansClusterer,
        cost_map: np.ndarray,
    ):
        """
        Args:
            graph: 3D path graph
            clusterer: Fitted KMeansClusterer with centroids
            cost_map: 3D cost array for computing mean costs
        """
        self.graph = graph
        self.clusterer = clusterer
        self.cost_map = cost_map
        
        # Precompute centroid costs for efficiency
        self.centroid_costs = self._compute_centroid_costs()
        
        print(f"[AdvancedHeuristic] Initialized with {clusterer.n_clusters} clusters")
    
    def _compute_centroid_costs(self) -> np.ndarray:
        """
        Precompute cost values at each cluster centroid.
        
        Returns:
            Array of cost values at centroid positions
        """
        costs = []
        for centroid in self.clusterer.centroids:
            # Convert centroid coordinates to grid indices
            layer = int(round(centroid[0]))
            row = int(round(centroid[1]))
            col = int(round(centroid[2]))
            
            # Ensure within bounds
            layer = max(0, min(layer, self.cost_map.shape[0] - 1))
            row = max(0, min(row, self.cost_map.shape[1] - 1))
            col = max(0, min(col, self.cost_map.shape[2] - 1))
            
            costs.append(float(self.cost_map[layer, row, col]))
        
        return np.array(costs)
    
    def compute_h_Dist(
        self,
        current_node: int,
        goal_node: int,
        open_set_nodes: Optional[Set[Tuple[int, int, int]]] = None,
    ) -> float:
        """
        Compute global heuristic distance h_Dist per Eq. 24.
        
        h_Dist = h_heuDist × EuclideanDistance(current, goal)
        
        where:
        h_heuDist = min(
            mean_cost_open_vertices,
            mean_cost_cluster_centroids
        )
        
        Args:
            current_node: Current node index
            goal_node: Goal node index
            open_set_nodes: Set of (layer, row, col) tuples in open list
            
        Returns:
            Global heuristic value h_Dist
        """
        # Get coordinates
        curr_coords = self.graph.centroid(*self.graph.unpack_index(current_node))
        goal_coords = self.graph.centroid(*self.graph.unpack_index(goal_node))
        
        # Euclidean distance
        euclidean_dist = float(np.linalg.norm(goal_coords - curr_coords))
        
        # Compute h_heuDist factor
        
        # Option 1: Mean cost of open vertices
        if open_set_nodes and len(open_set_nodes) > 0:
            open_costs = []
            for (layer, row, col) in open_set_nodes:
                # Ensure within bounds
                layer = max(0, min(layer, self.cost_map.shape[0] - 1))
                row = max(0, min(row, self.cost_map.shape[1] - 1))
                col = max(0, min(col, self.cost_map.shape[2] - 1))
                open_costs.append(float(self.cost_map[layer, row, col]))
            
            mean_open_cost = np.mean(open_costs)
        else:
            mean_open_cost = float('inf')
        
        # Option 2: Mean cost of cluster centroids
        mean_centroid_cost = np.mean(self.centroid_costs)
        
        # Take minimum for admissibility
        h_heuDist = min(mean_open_cost, mean_centroid_cost)
        
        # Global heuristic
        h_Dist = h_heuDist * euclidean_dist
        
        return h_Dist
    
    def compute_h_Drctn(self, current_node: int) -> float:
        """
        Compute local heuristic direction h_Drctn per Eq. 25.
        
        h_Drctn = Distance(current, nearest_centroid)
        
        Args:
            current_node: Current node index
            
        Returns:
            Local heuristic value h_Drctn
        """
        # Get current coordinates
        curr_coords = self.graph.centroid(*self.graph.unpack_index(current_node))
        
        # Find nearest centroid
        nearest_centroid, _ = self.clusterer.get_nearest_centroid(curr_coords)
        
        # Euclidean distance to nearest centroid
        h_Drctn = float(np.linalg.norm(nearest_centroid - curr_coords))
        
        return h_Drctn
    
    def create_h_Dist_fn(self) -> callable:
        """
        Create a callable function for h_Dist computation.
        
        Returns:
            Function with signature: h_Dist_fn(current, goal, open_nodes) -> float
        """
        def h_Dist_fn(
            current_node: int,
            goal_node: int,
            open_set_nodes: Optional[Set[Tuple[int, int, int]]] = None
        ) -> float:
            return self.compute_h_Dist(current_node, goal_node, open_set_nodes)
        
        return h_Dist_fn
    
    def create_h_Drctn_fn(self) -> callable:
        """
        Create a callable function for h_Drctn computation.
        
        Returns:
            Function with signature: h_Drctn_fn(current) -> float
        """
        def h_Drctn_fn(current_node: int) -> float:
            return self.compute_h_Drctn(current_node)
        
        return h_Drctn_fn