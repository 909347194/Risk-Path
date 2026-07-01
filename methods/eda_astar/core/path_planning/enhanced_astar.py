"""
Enhanced Cost A* Path Planning Algorithm with Advanced Heuristics

Implements the advanced heuristic functions from Pang et al. (2022):
- Eq. 24: Global heuristic distance (h_Dist)
- Eq. 25: Local heuristic direction (h_Drctn)
- Eq. 26: Adaptive heuristic switching

This is an enhanced version of the standard CostAStarSearcher that supports
cluster-based adaptive heuristics for improved search efficiency.
"""

from __future__ import annotations

import heapq
import numpy as np
from typing import Optional, List, Callable, Tuple, Any

try:
    from .graph import Grid3DPathGraph
except ImportError:
    from graph import Grid3DPathGraph


class EnhancedCostAStarSearcher:
    """Enhanced Cost A* with advanced heuristic functions (Eq. 24-26).
    
    This searcher implements the adaptive heuristic strategy from the paper:
    - Global heuristic (h_Dist): Based on mean cost statistics
    - Local heuristic (h_Drctn): Distance to nearest cluster centroid
    - Adaptive switching: Based on deviation threshold ε
    
    Algorithm 3: CostA* with advanced heuristics
    """
    
    def __init__(
        self,
        graph: Grid3DPathGraph,
        h_Dist_fn: Optional[Callable] = None,
        h_Drctn_fn: Optional[Callable] = None,
        epsilon: float = 0.2,
        start_coords: Optional[np.ndarray] = None,
        goal_coords: Optional[np.ndarray] = None,
        clusterer: Optional[Any] = None,
    ):
        """
        Initialize Enhanced CostA* searcher with advanced heuristics.
        
        Args:
            graph: 3D path graph
            h_Dist_fn: Global heuristic function (Eq. 24)
            h_Drctn_fn: Local heuristic function (Eq. 25)
            epsilon: Deviation threshold for adaptive switching (default 0.2)
            start_coords: Start position [x, y, z] for global track computation
            goal_coords: Goal position [x, y, z] for global track computation
            clusterer: KMeansClusterer for computing projection distances
        """
        self.graph = graph
        self.h_Dist_fn = h_Dist_fn
        self.h_Drctn_fn = h_Drctn_fn
        self.epsilon = epsilon
        
        # Store parameters for h_Dist_cen computation
        self.start_coords = start_coords
        self.goal_coords = goal_coords
        self.clusterer = clusterer
        
        # Precompute global track direction vector
        if start_coords is not None and goal_coords is not None:
            self.global_track_dir = np.array(goal_coords) - np.array(start_coords)
            self.global_track_length = np.linalg.norm(self.global_track_dir)
            if self.global_track_length > 1e-10:
                self.global_track_unit = self.global_track_dir / self.global_track_length
            else:
                self.global_track_unit = np.array([1.0, 0.0, 0.0])
        else:
            self.global_track_dir = None
            self.global_track_length = None
            self.global_track_unit = None
        
        print(f"[EnhancedCostA*] Initialized:")
        print(f"  - Epsilon (ε): {epsilon}")
        print(f"  - Advanced heuristics: {'Enabled' if h_Dist_fn and h_Drctn_fn else 'Disabled'}")
        if self.global_track_dir is not None:
            print(f"  - Global track: length={self.global_track_length:.2f}m")
    
    def _heuristic_fallback(self, from_index: int, to_index: int) -> float:
        """Fallback heuristic: Simple Euclidean distance."""
        return self.graph.transition_distance(from_index, to_index)
    
    def _compute_adaptive_heuristic(
        self,
        current_node: int,
        goal_node: int,
        open_set_nodes: Optional[set] = None,
    ) -> float:
        """
        Compute adaptive heuristic h(c) per Eq. 26.
        
        h(c) = {
            h_Drctn,  if (h_Drctn - h_Dist_cen) / h_Dist_cen < ε
            h_Dist,   otherwise
        }
        
        Args:
            current_node: Current node index
            goal_node: Goal node index
            open_set_nodes: Set of nodes in open list (for h_Dist computation)
            
        Returns:
            Adaptive heuristic value h(c)
        """
        # If advanced heuristics not provided, use fallback
        if self.h_Dist_fn is None or self.h_Drctn_fn is None:
            return self._heuristic_fallback(current_node, goal_node)
        
        try:
            # Compute both heuristics
            h_Dist = self.h_Dist_fn(current_node, goal_node, open_set_nodes)
            h_Drctn = self.h_Drctn_fn(current_node)
            
            # Compute reference distance to centroid projection (h_Dist_cen)
            h_Dist_cen = self._compute_reference_distance(current_node, goal_node)
            
            # Adaptive switching per Eq. 26
            if h_Dist_cen > 1e-10:  # Avoid division by zero
                deviation = (h_Drctn - h_Dist_cen) / h_Dist_cen
                
                if deviation < self.epsilon:
                    # Close to centroid: use local heuristic
                    return h_Drctn
                else:
                    # Far from centroid: use global heuristic
                    return h_Dist
            else:
                # Fallback to global heuristic
                return h_Dist
        except Exception as e:
            # On error, fallback to simple Euclidean
            print(f"  [Warning] Heuristic computation failed: {e}, using fallback")
            return self._heuristic_fallback(current_node, goal_node)
    
    def _compute_reference_distance(
        self,
        current_node: int,
        goal_node: int,
    ) -> float:
        """
        Compute h_Dist_cen: Distance from current point to the projection of
        nearest cluster centroid onto the global track.
        
        Per paper definition:
        "hDist cen is the heuristic distance from the current point to the point 
        that is projected from cluster centroid on the global track."
        
        Geometric interpretation:
        - Global track: line from start to goal
        - Find nearest cluster centroid to current position
        - Project centroid onto global track
        - Return distance from current position to this projected point
        
        Args:
            current_node: Current node index
            goal_node: Goal node index (for reference)
            
        Returns:
            Reference distance h_Dist_cen in meters
        """
        # Fallback if required data not available
        if (self.clusterer is None or 
            self.start_coords is None or 
            self.goal_coords is None or
            self.global_track_unit is None):
            return 100.0  # Default fallback
        
        try:
            # Get current position coordinates
            layer, row, col = self.graph.unpack_index(current_node)
            current_coords = np.array(self.graph.centroid(layer, row, col))
            
            # Find nearest cluster centroid
            nearest_centroid, _ = self.clusterer.get_nearest_centroid(current_coords)
            
            # Project centroid onto global track
            # Vector from start to centroid
            start_to_centroid = nearest_centroid - self.start_coords
            
            # Projection scalar (how far along the global track the projection falls)
            t = np.dot(start_to_centroid, self.global_track_unit)
            
            # Clamp t to [0, global_track_length] to stay within track segment
            t = max(0.0, min(t, self.global_track_length))
            
            # Compute projected point on global track
            projected_point = self.start_coords + t * self.global_track_unit
            
            # Compute distance from current position to projected point
            h_Dist_cen = np.linalg.norm(current_coords - projected_point)
            
            return float(h_Dist_cen)
            
        except Exception as e:
            print(f"  [Warning] h_Dist_cen computation failed: {e}, using fallback")
            return 100.0
    
    def search(
        self,
        start_layer: int,
        start_row: int,
        start_col: int,
        goal_layer: int,
        goal_row: int,
        goal_col: int,
        cost_map: np.ndarray | None = None,
        risk_weight: float = 1.0,
        distance_weight: float = 1.0,
    ) -> Optional[List[int]]:
        """
        Find minimum cost path using enhanced A* with adaptive heuristics.
        
        Implements Algorithm 3 from Pang et al. (2022) with Eq. 24-26.
        
        Args:
            start_layer, start_row, start_col: Start node coordinates
            goal_layer, goal_row, goal_col: Goal node coordinates
            cost_map: 3D array (layer, row, col) with integrated vertex costs
            risk_weight: Weight for risk/cost component
            distance_weight: Weight for distance component
            
        Returns:
            List of node indices representing the optimal path,
            or None if no path exists
        """
        # Convert coordinates to node indices
        start_node = self.graph.index(start_layer, start_row, start_col)
        goal_node = self.graph.index(goal_layer, goal_row, goal_col)
        
        # Set start and goal coordinates for h_Dist_cen computation (if not already set)
        if self.start_coords is None or self.goal_coords is None:
            self.start_coords = np.array(self.graph.centroid(start_layer, start_row, start_col))
            self.goal_coords = np.array(self.graph.centroid(goal_layer, goal_row, goal_col))
            
            # Recompute global track direction
            self.global_track_dir = self.goal_coords - self.start_coords
            self.global_track_length = np.linalg.norm(self.global_track_dir)
            if self.global_track_length > 1e-10:
                self.global_track_unit = self.global_track_dir / self.global_track_length
            else:
                self.global_track_unit = np.array([1.0, 0.0, 0.0])
        
        # Validate nodes
        if not self.graph.is_within_bounds(start_layer, start_row, start_col):
            raise ValueError(f"Start node out of bounds")
        if not self.graph.is_within_bounds(goal_layer, goal_row, goal_col):
            raise ValueError(f"Goal node out of bounds")
        
        # Early termination
        if start_node == goal_node:
            return [start_node]
        
        # ===== A* Data Structures =====
        open_set = []
        counter = 0
        
        g_score = {start_node: 0.0}
        
        # Initial heuristic
        h_initial = self._compute_adaptive_heuristic(start_node, goal_node)
        f_score = {start_node: h_initial}
        
        came_from = {}
        closed_set = set()
        
        # Track open set nodes for h_Dist computation
        open_set_nodes = set()
        open_set_nodes.add((start_layer, start_row, start_col))
        
        heapq.heappush(open_set, (f_score[start_node], counter, start_node))
        
        # ===== Main Search Loop =====
        iterations = 0
        while open_set:
            iterations += 1
            _, _, current = heapq.heappop(open_set)
            
            # Goal test
            if current == goal_node:
                path = self._reconstruct_path(came_from, current)
                print(f"  [Enhanced A*] Path found in {iterations} iterations")
                return path
            
            # Skip if already processed
            if current in closed_set:
                continue
            
            closed_set.add(current)
            
            # Expand neighbors
            current_layer, current_row, current_col = self.graph.unpack_index(current)
            neighbors = self.graph.find_neighbors_and_costs(
                current_layer, current_row, current_col,
                cost_map=cost_map,
                risk_weight=risk_weight,
                distance_weight=distance_weight
            )
            
            for neighbor, edge_cost in neighbors:
                if neighbor in closed_set:
                    continue
                
                # Step 2: Compute g(c) - cumulative cost
                tentative_g = g_score[current] + edge_cost
                
                # If better path found
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    
                    # Step 3 & 4: Compute adaptive heuristic h(c) per Eq. 26
                    n_layer, n_row, n_col = self.graph.unpack_index(neighbor)
                    h_value = self._compute_adaptive_heuristic(
                        neighbor, goal_node, open_set_nodes
                    )
                    
                    # Step 5: Evaluate f(c) = g(c) + h(c)
                    f_score[neighbor] = tentative_g + h_value
                    
                    # Update open set tracking
                    open_set_nodes.add((n_layer, n_row, n_col))
                    
                    # Step 6: Add to open set
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
        
        # No path found
        print(f"  [Enhanced A*] No path found after {iterations} iterations")
        return None
    
    def _reconstruct_path(self, came_from: dict, current: int) -> List[int]:
        """Reconstruct path from came_from map."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
    def compute_path_metrics(
        self,
        path: List[int],
        cost_map: np.ndarray | None = None
    ) -> dict:
        """Compute detailed metrics for a given path."""
        if not path:
            return {"total_cost": 0.0, "total_distance": 0.0, "num_nodes": 0}
        
        total_distance = 0.0
        total_vertex_cost = 0.0
        
        for i, node in enumerate(path):
            if cost_map is not None:
                layer, row, col = self.graph.unpack_index(node)
                total_vertex_cost += float(cost_map[layer, row, col])
            
            if i > 0:
                total_distance += self.graph.transition_distance(path[i-1], node)
        
        return {
            "total_cost": total_vertex_cost,
            "total_distance": total_distance,
            "num_nodes": len(path),
            "avg_cost_per_node": total_vertex_cost / len(path) if path else 0.0,
        }