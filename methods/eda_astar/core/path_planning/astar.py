"""
Cost A* Path Planning Algorithm

Implements the A* search algorithm with risk-aware cost assessment.
This is a deterministic, greedy algorithm that finds the optimal path
by minimizing the total integrated cost.
"""

from __future__ import annotations

import heapq
import numpy as np
from typing import Optional, List

try:
    from .graph import Grid3DPathGraph
except ImportError:
    from graph import Grid3DPathGraph


class CostAStarSearcher:
    """Cost-based A* path planner for 3D UAV navigation.
    
    Algorithm Overview:
    1. Uses priority queue (min-heap) to explore nodes in order of f_score
    2. f_score = g_score + heuristic
       - g_score: Actual cost from start to current node
       - heuristic: Estimated cost from current to goal (Euclidean distance)
    3. Expands neighbors and updates costs if better path found
    4. Terminates when goal is reached or queue is empty
    
    Objective: Minimize total path cost CP = Σ cv_i where v_i ∈ V_P (Eq. 20)
    """
    
    def __init__(self, graph: Grid3DPathGraph):
        """
        Args:
            graph: 3D path graph for navigation
        """
        self.graph = graph
    
    def _heuristic(self, from_index: int, to_index: int) -> float:
        """Admissible heuristic: Euclidean distance between centroids.
        
        This heuristic is admissible (never overestimates) because:
        - Actual edge cost >= Euclidean distance
        - Ensures A* optimality
        
        Args:
            from_index: Current node index
            to_index: Goal node index
            
        Returns:
            Euclidean distance between nodes
        """
        return self.graph.transition_distance(from_index, to_index)
    
    def _reconstruct_path(self, came_from: dict, current: int) -> List[int]:
        """Reconstruct path from start to goal using parent pointers.
        
        Args:
            came_from: Dictionary mapping node -> parent node
            current: Goal node index
            
        Returns:
            List of node indices from start to goal
        """
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path
    
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
        """Find minimum cost path from start to goal using A* algorithm.
        
        Algorithm Steps:
        1. Initialize open set with start node
        2. While open set not empty:
           a. Pop node with lowest f_score
           b. If goal reached, reconstruct and return path
           c. Expand neighbors
           d. For each neighbor:
              - Calculate tentative g_score
              - If better path found, update and add to open set
        3. Return None if no path exists
        
        Args:
            start_layer, start_row, start_col: Start node coordinates
            goal_layer, goal_row, goal_col: Goal node coordinates
            cost_map: 3D array (layer, row, col) with integrated vertex costs
            risk_weight: Weight for risk/cost component in edge transition
            distance_weight: Weight for distance component in edge transition
            
        Returns:
            List of node indices representing the optimal path, 
            or None if no path exists
        """
        # Convert coordinates to node indices
        start_node = self.graph.index(start_layer, start_row, start_col)
        goal_node = self.graph.index(goal_layer, goal_row, goal_col)
        
        # Validate nodes are within bounds
        if not self.graph.is_within_bounds(start_layer, start_row, start_col):
            raise ValueError(f"Start node ({start_layer}, {start_row}, {start_col}) is out of bounds")
        if not self.graph.is_within_bounds(goal_layer, goal_row, goal_col):
            raise ValueError(f"Goal node ({goal_layer}, {goal_row}, {goal_col}) is out of bounds")
        
        # Early termination if start == goal
        if start_node == goal_node:
            return [start_node]
        
        # ===== A* Data Structures =====
        
        # Open set: Priority queue ordered by f_score
        # Format: (f_score, counter, node_index)
        # counter is used as tie-breaker
        open_set = []
        counter = 0
        
        # g_score[node] = cost from start to node
        g_score = {start_node: 0.0}
        
        # f_score[node] = g_score[node] + heuristic(node, goal)
        f_score = {start_node: self._heuristic(start_node, goal_node)}
        
        # Track path reconstruction: came_from[child] = parent
        came_from = {}
        
        # Closed set: Already processed nodes
        closed_set = set()
        
        # Initialize open set with start node
        heapq.heappush(open_set, (f_score[start_node], counter, start_node))
        
        # ===== Main Search Loop =====
        
        while open_set:
            # Pop node with lowest f_score
            _, _, current = heapq.heappop(open_set)
            
            # Goal test
            if current == goal_node:
                return self._reconstruct_path(came_from, current)
            
            # Skip if already processed
            if current in closed_set:
                continue
            
            # Mark as processed
            closed_set.add(current)
            
            # Expand neighbors
            current_layer, current_row, current_col = self.graph.unpack_index(current)
            neighbors = self.graph.find_neighbors_and_costs(
                current_layer, current_row, current_col,
                cost_map=cost_map,
                risk_weight=risk_weight,
                distance_weight=distance_weight
            )
            
            # Process each neighbor
            for neighbor, edge_cost in neighbors:
                # Skip already processed nodes
                if neighbor in closed_set:
                    continue
                
                # Calculate tentative g_score: g(current) + edge_cost
                tentative_g = g_score[current] + edge_cost
                
                # If this path to neighbor is better than any previous one
                if tentative_g < g_score.get(neighbor, float('inf')):
                    # Update parent pointer
                    came_from[neighbor] = current
                    
                    # Update g_score and f_score
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + self._heuristic(neighbor, goal_node)
                    
                    # Add to open set (may have duplicates, but closed_set handles that)
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
        
        # No path found (open set exhausted)
        return None
    
    def compute_path_metrics(
        self,
        path: List[int],
        cost_map: np.ndarray | None = None
    ) -> dict:
        """Compute detailed metrics for a given path.
        
        Args:
            path: List of node indices
            cost_map: 3D cost array for computing vertex costs
            
        Returns:
            Dictionary with path statistics:
            - total_cost: Sum of vertex costs
            - total_distance: Sum of edge distances
            - num_nodes: Number of waypoints
            - avg_cost_per_node: Average vertex cost
        """
        if not path:
            return {
                "total_cost": 0.0, 
                "total_distance": 0.0, 
                "num_nodes": 0
            }
        
        total_distance = 0.0
        total_vertex_cost = 0.0
        
        for i, node in enumerate(path):
            # Accumulate vertex cost (Eq. 20)
            if cost_map is not None:
                layer, row, col = self.graph.unpack_index(node)
                total_vertex_cost += float(cost_map[layer, row, col])
            
            # Accumulate edge distance
            if i > 0:
                total_distance += self.graph.transition_distance(path[i-1], node)
        
        return {
            "total_cost": total_vertex_cost,
            "total_distance": total_distance,
            "num_nodes": len(path),
            "avg_cost_per_node": total_vertex_cost / len(path) if path else 0.0,
        }
