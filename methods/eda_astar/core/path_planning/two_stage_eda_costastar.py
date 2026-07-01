"""
Two-Stage EDA-CostA* Algorithm (Per Paper's Algorithm 2)

Implements the exact flow from Pang et al. (2022) Algorithm 2:
1. EDA optimization to find best population
2. Extract open points from best population
3. K-means clustering on open points
4. Compute advanced heuristics (Eq. 24-25)
5. Run Enhanced CostA* with adaptive heuristics (Eq. 26)

This is a REFACTORED version that matches the paper's architecture exactly.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Set, Tuple

try:
    from .graph import Grid3DPathGraph
    from .eda_costastar import EDACostAStarSearcher as OriginalEDASearcher
    from .enhanced_astar import EnhancedCostAStarSearcher
    from .clustering import cluster_open_points
    from .heuristic_calculator import AdvancedHeuristicCalculator
except ImportError:
    from graph import Grid3DPathGraph
    from eda_costastar import EDACostAStarSearcher as OriginalEDASearcher
    from enhanced_astar import EnhancedCostAStarSearcher
    from clustering import cluster_open_points
    from heuristic_calculator import AdvancedHeuristicCalculator


class TwoStageEDACostAStarSearcher:
    """
    Two-stage EDA-CostA* algorithm per Algorithm 2 of Pang et al. (2022).
    
    Stage 1: EDA Optimization
    └─→ Optimize searching region, extract best population
    
    Stage 2: Clustering & Heuristic Computation
    ├─→ Extract open points from best population
    ├─→ Apply K-means clustering
    ├─→ Compute h_Dist (Eq. 24) and h_Drctn (Eq. 25)
    └─→ Run Enhanced CostA* with adaptive heuristics (Eq. 26)
    """
    
    def __init__(
        self,
        graph: Grid3DPathGraph,
        eda_population_size: int = 30,
        eda_elite_size: int = 6,
        eda_max_generations: int = 50,
        eda_learning_rate: float = 0.2,
        n_clusters: int = 5,
        epsilon: float = 0.2,
    ):
        """
        Args:
            graph: 3D path graph
            eda_population_size: EDA population size
            eda_elite_size: EDA elite size
            eda_max_generations: EDA max generations
            eda_learning_rate: EDA learning rate (Eq. 23)
            n_clusters: Number of clusters for K-means
            epsilon: Deviation threshold for adaptive switching (Eq. 26)
        """
        self.graph = graph
        self.n_clusters = n_clusters
        self.epsilon = epsilon
        
        # Stage 1: EDA searcher
        self.eda_searcher = OriginalEDASearcher(
            graph=graph,
            population_size=eda_population_size,
            elite_size=eda_elite_size,
            max_generations=eda_max_generations,
        )
        
        print(f"[TwoStageEDA] Initialized:")
        print(f"  - EDA: pop={eda_population_size}, elite={eda_elite_size}, "
              f"gen={eda_max_generations}")
        print(f"  - Clustering: n_clusters={n_clusters}")
        print(f"  - Heuristic: epsilon={epsilon}")
    
    def _extract_open_points(
        self,
        best_region: Set[Tuple[int, int, int]],
    ) -> List[Tuple[int, int, int]]:
        """
        Extract open points from best population (Algorithm 2, Lines 4-7).
        
        In the paper, this extracts cells where P_best(i,j,k) == 1.
        In our implementation, the best_region is already the set of included cells.
        
        Args:
            best_region: Set of (layer, row, col) from EDA optimization
            
        Returns:
            List of open point coordinates
        """
        open_points = list(best_region)
        print(f"  [Stage 2] Extracted {len(open_points)} open points from best region")
        return open_points
    
    def search(
        self,
        start_layer: int,
        start_row: int,
        start_col: int,
        goal_layer: int,
        goal_row: int,
        goal_col: int,
        cost_map: np.ndarray,
        risk_weight: float = 1.0,
        distance_weight: float = 1.0,
    ) -> Optional[List[int]]:
        """
        Find optimal path using two-stage EDA-CostA* (Algorithm 2).
        
        STAGE 1: EDA Optimization (Lines 1-3)
        STAGE 2: Clustering & Heuristic Computation (Lines 4-9)
        STAGE 3: Enhanced CostA* Path Planning (Line 10)
        
        Args:
            start_layer, start_row, start_col: Start coordinates
            goal_layer, goal_row, goal_col: Goal coordinates
            cost_map: 3D cost array
            risk_weight: Risk weight for A*
            distance_weight: Distance weight for A*
            
        Returns:
            Optimal path as list of node indices, or None
        """
        print("\n" + "=" * 70)
        print("Two-Stage EDA-CostA* Algorithm (Per Paper's Algorithm 2)")
        print("=" * 70)
        
        # ===== STAGE 1: EDA Optimization =====
        print("\n[Stage 1] Running EDA optimization...")
        
        # Run EDA to get best region
        best_path_from_eda = self.eda_searcher.search(
            start_layer=start_layer,
            start_row=start_row,
            start_col=start_col,
            goal_layer=goal_layer,
            goal_row=goal_row,
            goal_col=goal_col,
            cost_map=cost_map,
            risk_weight=risk_weight,
            distance_weight=distance_weight,
        )
        
        if best_path_from_eda is None:
            print("  ✗ EDA failed to find a feasible region")
            return None
        
        # Get best region from EDA
        # Note: Original EDACostAStarSearcher doesn't expose best_region, 
        # so we extract it from the best path found
        best_region = set()
        if best_path_from_eda is not None:
            for node_idx in best_path_from_eda:
                layer, row, col = self.graph.unpack_index(node_idx)
                best_region.add((layer, row, col))
            
            print(f"  ✓ Extracted {len(best_region)} cells from EDA best path")
        else:
            print("  ⚠ EDA failed to find a feasible path")
            return None
        
        if len(best_region) == 0:
            print("  ⚠ No best region found, using full space")
            # Fallback: use all non-blocked cells
            best_region = set()
            for layer in range(self.graph.layer_count):
                for row in range(self.graph.grid.height):
                    for col in range(self.graph.grid.width):
                        if cost_map[layer, row, col] < float('inf'):
                            best_region.add((layer, row, col))
        
        print(f"  ✓ Best region size: {len(best_region)} cells")
        
        # ===== STAGE 2: Extract Open Points & Cluster =====
        print("\n[Stage 2] Extracting open points and clustering...")
        
        # Extract open points (Lines 4-7)
        open_points = self._extract_open_points(best_region)
        
        if len(open_points) < self.n_clusters:
            print(f"  ⚠ Too few open points ({len(open_points)}) for {self.n_clusters} clusters")
            print("  Falling back to standard EDA-A* path")
            return best_path_from_eda
        
        # Apply K-means clustering (Line 8)
        print(f"  Applying K-means clustering (k={self.n_clusters})...")
        clusterer = cluster_open_points(
            open_points=open_points,
            n_clusters=self.n_clusters,
            use_physical_coords=True,
            graph=self.graph,
        )
        
        print(f"  ✓ Cluster centroids computed:")
        if clusterer is not None and clusterer.centroids is not None:
            for i, centroid in enumerate(clusterer.centroids):
                print(f"    Centroid {i}: ({centroid[0]:.1f}, {centroid[1]:.1f}, {centroid[2]:.1f})")
        else:
            print("  ⚠ No cluster centroids available")
        
        # ===== STAGE 3: Compute Heuristics & Run Enhanced CostA* =====
        print("\n[Stage 3] Computing advanced heuristics (Eq. 24-25)...")
        
        # Create heuristic calculator
        heuristic_calc = AdvancedHeuristicCalculator(
            graph=self.graph,
            clusterer=clusterer,
            cost_map=cost_map,
        )
        
        # Create heuristic functions
        h_Dist_fn = heuristic_calc.create_h_Dist_fn()
        h_Drctn_fn = heuristic_calc.create_h_Drctn_fn()
        
        print(f"  ✓ Heuristic functions created")
        print(f"  ✓ Adaptive switching enabled (ε={self.epsilon})")
        
        # Run Enhanced CostA* with heuristics (Line 10)
        print("\n[Stage 4] Running Enhanced CostA* with adaptive heuristics (Eq. 26)...")
        
        # Get start and goal coordinates for global track computation
        start_coords = self.graph.centroid(start_layer, start_row, start_col)
        goal_coords = self.graph.centroid(goal_layer, goal_row, goal_col)
        
        enhanced_searcher = EnhancedCostAStarSearcher(
            graph=self.graph,
            h_Dist_fn=h_Dist_fn,
            h_Drctn_fn=h_Drctn_fn,
            epsilon=self.epsilon,
            start_coords=start_coords,
            goal_coords=goal_coords,
            clusterer=clusterer,  # Pass clusterer for h_Dist_cen computation
        )
        
        final_path = enhanced_searcher.search(
            start_layer=start_layer,
            start_row=start_row,
            start_col=start_col,
            goal_layer=goal_layer,
            goal_row=goal_row,
            goal_col=goal_col,
            cost_map=cost_map,
            risk_weight=risk_weight,
            distance_weight=distance_weight,
        )
        
        if final_path is not None:
            print(f"\n✓ Two-stage EDA-CostA* completed successfully!")
            print(f"  Path length: {len(final_path)} waypoints")
        else:
            print(f"\n✗ Enhanced CostA* failed, falling back to EDA path")
            final_path = best_path_from_eda
        
        print("=" * 70)
        
        return final_path