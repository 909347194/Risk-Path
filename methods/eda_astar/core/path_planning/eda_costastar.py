"""
EDA-A* Hybrid Algorithm (CORRECTED per Algorithm 1, Pang et al. 2022)

Implements the Estimation of Distribution Algorithm (EDA) integrated with 
A* algorithm for UAV path optimization.

KEY INSIGHT FROM PAPER:
- EDA optimizes the SEARCHING REGION (feasible airspace units), not the path directly
- A* finds the path within that optimized region
- This is a TWO-LOOP algorithm:
  * Outer loop (EDA): Optimize which airspace units to include
  * Inner loop (A*): Find optimal path in the feasible region

Based on: Pang et al. (2022) - Section 3.3, Algorithm 1, Eq. 23
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple

try:
    from .graph import Grid3DPathGraph
    from .astar import CostAStarSearcher
except ImportError:
    from graph import Grid3DPathGraph
    from astar import CostAStarSearcher


class EDACostAStarSearcher:
    """EDA-A* hybrid algorithm for UAV path optimization.
    
    CORRECTED IMPLEMENTATION per Algorithm 1 (Pang et al. 2022):
    
    KEY CONCEPT: EDA optimizes the SEARCHING REGION (feasible airspace units),
    not the path directly. Each individual is a 3D binary mask.
    
    Algorithm Structure:
    ┌──────────────────────────────────────────────────────────┐
    │  OUTER LOOP: EDA (Optimize Searching Region)             │
    ├──────────────────────────────────────────────────────────┤
    │  1. Initialize probability matrix p (uniform 0.5)        │
    │  2. FOR each generation:                                 │
    │     a. Sample n_ppl species (binary masks)               │
    │        species{j} = 1 .* (rand(size(Cost)) < p)          │
    │     b. FOR each species:                                 │
    │        - Run A* within masked region                     │
    │        - Fitness = path cost (inf if no path)            │
    │     c. Select elite_size dominant populations            │
    │     d. Update probability (Eq. 23):                      │
    │        p_{i+1} = (1-α)*p_i + α*(D_s/N_s)                │
    │  3. Return best path found                               │
    └──────────────────────────────────────────────────────────┘
    """
    
    def __init__(
        self,
        graph: Grid3DPathGraph,
        population_size: int = 20,
        elite_size: int = 4,
        max_generations: int = 30,
        learning_rate: float = 0.2,
    ):
        """
        Args:
            graph: 3D path graph
            population_size: Number of candidate searching regions (n_ppl)
            elite_size: Number of dominant populations for model update
            max_generations: Maximum EDA iterations (n_iter)
            learning_rate: Learning rate α in Eq. 23 (l_rate)
        """
        self.graph = graph
        self.population_size = population_size
        self.elite_size = elite_size
        self.max_generations = max_generations
        self.learning_rate = learning_rate
        
        # Dimensions of probability matrix (matches Cost map)
        self.layers = graph.layer_count
        self.height = graph.grid.height
        self.width = graph.grid.width
        
        # A* searcher for inner loop evaluation
        self.astar_searcher = CostAStarSearcher(graph)
    
    # ========== Probability Model Methods ==========
    
    def _initialize_probability_matrix(self) -> np.ndarray:
        """Initialize probability matrix p with uniform distribution.
        
        Per Algorithm 1: Each cell has independent probability of being selected.
        Start with 0.5 (equal chance for all cells).
        
        Returns:
            Array of shape (layers, height, width) with values in [0, 1]
        """
        return np.full((self.layers, self.height, self.width), 0.5, dtype=float)
    
    def _sample_species(self, prob_matrix: np.ndarray) -> List[np.ndarray]:
        """Sample population_size species (searching spaces) from probability matrix.
        
        Per Algorithm 1 Line 6-7:
            r = rand(size(Cost))
            species{j,1} = 1 .* (r{j,1} < p{i,1})
        
        This is vectorized Bernoulli sampling for efficiency.
        
        Args:
            prob_matrix: Current probability matrix p
            
        Returns:
            List of binary masks, each of shape (layers, height, width)
        """
        species_list = []
        for _ in range(self.population_size):
            # Generate random matrix r ~ U(0, 1)
            r = np.random.rand(self.layers, self.height, self.width)
            # Binary mask: 1 if r < p, else 0
            mask = (r < prob_matrix).astype(np.int32)
            species_list.append(mask)
        return species_list
    
    def _evaluate_fitness(
        self, 
        mask: np.ndarray, 
        start_idx: int, 
        goal_idx: int, 
        cost_map: np.ndarray,
        risk_weight: float = 1.0,
        distance_weight: float = 1.0,
    ) -> Tuple[float, Optional[List[int]]]:
        """Evaluate fitness by running A* within the masked region.
        
        Per Algorithm 1 Line 12:
            path = A*(OD, species, obstacle)
            TotalCost = FitnessValue(path)
        
        Cells with mask=0 are blocked (infinite cost).
        
        Args:
            mask: Binary mask (1=feasible, 0=blocked)
            start_idx: Start node index
            goal_idx: Goal node index
            cost_map: Original cost map
            risk_weight: Risk weight for A*
            distance_weight: Distance weight for A*
            
        Returns:
            (fitness, path) tuple
            - fitness = total cost (lower is better, inf if no path)
            - path = list of node indices or None
        """
        # Create masked cost map: block cells where mask=0
        masked_cost = cost_map.copy()
        masked_cost[mask == 0] = float('inf')
        
        # Ensure start and goal are not blocked
        s_layer, s_row, s_col = self.graph.unpack_index(start_idx)
        g_layer, g_row, g_col = self.graph.unpack_index(goal_idx)
        
        if masked_cost[s_layer, s_row, s_col] == float('inf') or \
           masked_cost[g_layer, g_row, g_col] == float('inf'):
            return (float('inf'), None)
        
        # Run A* on the masked cost map
        try:
            path = self.astar_searcher.search(
                start_layer=s_layer,
                start_row=s_row,
                start_col=s_col,
                goal_layer=g_layer,
                goal_row=g_row,
                goal_col=g_col,
                cost_map=masked_cost,
                risk_weight=risk_weight,
                distance_weight=distance_weight,
            )
            
            if path is None:
                return (float('inf'), None)
            
            # Fitness = total path cost (from original cost_map)
            total_cost = sum(float(cost_map[self.graph.unpack_index(n)]) for n in path)
            return (total_cost, path)
        
        except Exception as e:
            print(f"    [Warning] A* evaluation failed: {e}")
            return (float('inf'), None)
    
    def _update_probability_matrix(
        self, 
        p_current: np.ndarray, 
        elite_masks: List[np.ndarray]
    ) -> np.ndarray:
        """Update probability matrix using Eq. (23).
        
        Per Algorithm 1 Line 18:
            p_{i+1} = (1 - l_rate) * p_i + l_rate * (D_s / N_s)
        
        Where:
        - D_s = count of how often each cell appears in elite populations
        - N_s = normalization factor (can be number of elites)
        
        Args:
            p_current: Current probability matrix p_i
            elite_masks: List of binary masks from elite individuals
            
        Returns:
            Updated probability matrix p_{i+1}
        """
        # D_s / N_s: Average of elite masks (element-wise mean)
        # This represents the "vote" from dominant populations
        ds_mean = np.mean(elite_masks, axis=0, dtype=float)
        
        # Update rule: Eq. 23
        p_next = (1 - self.learning_rate) * p_current + \
                 self.learning_rate * ds_mean
        
        # Clip to valid probability range [0, 1]
        p_next = np.clip(p_next, 0.0, 1.0)
        
        return p_next
    
    # ========== Main Search Method (Algorithm 1) ==========
    
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
        """Execute Algorithm 1: Hybrid EDA-A* for cost-based path planning.
        
        OUTER LOOP: EDA optimizes searching region (binary masks)
        INNER LOOP: A* finds path within each region
        
        Args:
            start_layer, start_row, start_col: Start coordinates
            goal_layer, goal_row, goal_col: Goal coordinates
            cost_map: 3D cost array (layers, height, width)
            risk_weight: Weight for risk component
            distance_weight: Weight for distance component
            
        Returns:
            Optimal path as list of node indices, or None if not found
        """
        start_idx = self.graph.index(start_layer, start_row, start_col)
        goal_idx = self.graph.index(goal_layer, goal_row, goal_col)
        
        # Validate bounds
        if not self.graph.is_within_bounds(start_layer, start_row, start_col):
            raise ValueError(f"Start node out of bounds: ({start_layer}, {start_row}, {start_col})")
        if not self.graph.is_within_bounds(goal_layer, goal_row, goal_col):
            raise ValueError(f"Goal node out of bounds: ({goal_layer}, {goal_row}, {goal_col})")
        
        print(f"  EDA-A*: Population={self.population_size}, "
              f"Elite={self.elite_size}, Generations={self.max_generations}, "
              f"LearningRate={self.learning_rate}")
        
        # ===== Step 1: Initialize probability matrix p =====
        print(f"  [EDA] Initializing probability matrix...")
        p = self._initialize_probability_matrix()
        
        best_path = None
        best_fitness = float('inf')
        
        # ===== Step 2: EDA Main Loop (Outer Loop) =====
        print(f"  [EDA] Optimizing searching region...")
        
        for gen in range(self.max_generations):
            # --- Line 5-9: Sample species (searching spaces) ---
            species = self._sample_species(p)
            
            # --- Line 11-15: Evaluate fitness for each species (Inner Loop) ---
            fitness_values = []
            paths = []
            
            for j, mask in enumerate(species):
                fitness, path = self._evaluate_fitness(
                    mask=mask,
                    start_idx=start_idx,
                    goal_idx=goal_idx,
                    cost_map=cost_map,
                    risk_weight=risk_weight,
                    distance_weight=distance_weight,
                )
                fitness_values.append(fitness)
                paths.append(path)
            
            # --- Line 16: Eliminate populations with no feasible path ---
            # Filter to only feasible solutions
            feasible_indices = [i for i, f in enumerate(fitness_values) if f < float('inf')]
            
            if not feasible_indices:
                print(f"    Gen {gen+1:3d}: No feasible paths found. "
                      f"Increasing exploration...")
                # If no feasible path, increase probabilities to explore more space
                p = np.clip(p + 0.05, 0.0, 1.0)
                continue
            
            # --- Line 17-18: Sort and select dominant populations ---
            feasible_solutions = [(i, fitness_values[i]) for i in feasible_indices]
            feasible_solutions.sort(key=lambda x: x[1])  # Sort by fitness (lower is better)
            
            # Select top elite_size individuals (or all if fewer than elite_size)
            num_elites = min(self.elite_size, len(feasible_solutions))
            elite_indices = [idx for idx, _ in feasible_solutions[:num_elites]]
            elite_masks = [species[idx] for idx in elite_indices]
            
            current_best_fit = feasible_solutions[0][1]
            current_best_path = paths[feasible_solutions[0][0]]
            
            # Update global best
            if current_best_fit < best_fitness:
                best_fitness = current_best_fit
                best_path = current_best_path
            
            num_feasible = len(feasible_indices)
            print(f"    Gen {gen+1:3d}: Best fitness={current_best_fit:.2f}, "
                  f"Feasible={num_feasible}/{self.population_size}")
            
            # --- Line 19: Update probability matrix (Eq. 23) ---
            p = self._update_probability_matrix(p, elite_masks)
            
            # --- Convergence check ---
            # If probability matrix has converged (all values near 0 or 1)
            if np.all((p < 0.05) | (p > 0.95)):
                print(f"    [EDA] Probability matrix converged at generation {gen+1}")
                break
        
        # ===== Step 3: Return best path =====
        if best_path is None:
            print(f"  [EDA] Failed to find a feasible path after {self.max_generations} generations.")
            return None
        
        print(f"  [EDA] Optimization complete. Best cost: {best_fitness:.2f}")
        return best_path
    
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
            Dictionary with path statistics
        """
        if not path:
            return {"total_cost": 0.0, "total_distance": 0.0, "num_nodes": 0}
        
        return self.astar_searcher.compute_path_metrics(path, cost_map)
