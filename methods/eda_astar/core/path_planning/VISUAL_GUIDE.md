# Path Planning Module - Visual Guide

## Module Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    path_planning/ Module                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  graph.py - 3D Navigation Graph                         │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  Grid3DPathGraph                                        │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Node Indexing:                                │     │   │
│  │  │  - index(layer, row, col) → int               │     │   │
│  │  │  - unpack_index(int) → (layer, row, col)      │     │   │
│  │  │  - is_within_bounds()                         │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Spatial Operations:                           │     │   │
│  │  │  - centroid() → [x, y, z]                     │     │   │
│  │  │  - neighbor_indices() → [neighbors]           │     │   │
│  │  │  - transition_distance()                      │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Edge Cost Computation:                        │     │   │
│  │  │  - transition_cost()                          │     │   │
│  │  │    = distance + risk + vertical               │     │   │
│  │  │  - is_safe_transition()                       │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  astar.py - Cost A* Algorithm                           │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  CostAStarSearcher                                      │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Algorithm: Deterministic, Greedy              │     │   │
│  │  │  1. Initialize open set                       │     │   │
│  │  │  2. Pop lowest f_score node                   │     │   │
│  │  │  3. Expand neighbors                          │     │   │
│  │  │  4. Update if better path                     │     │   │
│  │  │  5. Repeat until goal                         │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Key Methods:                                  │     │   │
│  │  │  - _heuristic() → Euclidean distance          │     │   │
│  │  │  - search() → optimal path                    │     │   │
│  │  │  - compute_path_metrics()                     │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           ↓                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  eda_costastar.py - EDA-CostA* Algorithm                │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │  EDACostAStarSearcher                                   │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Algorithm: Evolutionary + Local Search        │     │   │
│  │  │  ┌───────────────────────────────────────┐   │     │   │
│  │  │  │  Phase 1: Initialization              │   │     │   │
│  │  │  │  - Generate population (random A*)    │   │     │   │
│  │  │  └───────────────────────────────────────┘   │     │   │
│  │  │  ┌───────────────────────────────────────┐   │     │   │
│  │  │  │  Phase 2: Evolution Loop              │   │     │   │
│  │  │  │  1. Evaluate fitness                  │   │     │   │
│  │  │  │  2. Select elites (top-K)            │   │     │   │
│  │  │  │  3. Build probabilistic model         │   │     │   │
│  │  │  │  4. Sample new paths                  │   │     │   │
│  │  │  │  5. Apply mutation                    │   │     │   │
│  │  │  │  6. A* local refinement              │   │     │   │
│  │  │  │  7. Replace population               │   │     │   │
│  │  │  │  8. Repeat until convergence         │   │     │   │
│  │  │  └───────────────────────────────────────┘   │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  │  ┌───────────────────────────────────────────────┐     │   │
│  │  │  Key Methods:                                  │     │   │
│  │  │  - _evaluate_path()                           │     │   │
│  │  │  - _generate_initial_path()                   │     │   │
│  │  │  - _build_probabilistic_model()               │     │   │
│  │  │  - _sample_path_from_model()                  │     │   │
│  │  │  - _mutate_path()                             │     │   │
│  │  │  - _refine_with_astar()                       │     │   │
│  │  │  - search()                                   │     │   │
│  │  └───────────────────────────────────────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Cost A* Flow

```
Start Node ──→ [Priority Queue]
                    ↓
           Pop lowest f_score
                    ↓
           ┌────────┴────────┐
           │  Goal reached?  │
           └────────┬────────┘
                    │
              Yes ←─┴─→ No
               │         ↓
         Return Path  Expand Neighbors
                         ↓
                   Update g_scores
                         ↓
                   Push to Queue
                         ↓
                   Repeat ↑
```

### EDA-CostA* Flow

```
┌───────────────────────────────────────┐
│  Initialize Population                │
│  (Randomized A* × 50)                 │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Evaluate Fitness                     │
│  (cost + distance)                    │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Sort & Select Elite                  │
│  (Top 10)                             │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Build Probabilistic Model            │
│  P[layer, row, col]                   │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Sample New Paths                     │
│  (Forward sampling)                   │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Apply Mutation                       │
│  (Replace/Remove/Insert)              │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  A* Local Refinement                  │
│  (Optimize segments)                  │
└──────────────┬────────────────────────┘
               ↓
┌───────────────────────────────────────┐
│  Replace Population                   │
│  (Elites + Offspring)                 │
└──────────────┬────────────────────────┘
               ↓
        Convergence?
          │
    Yes ←─┴─→ No
     │        ↓
 Return Best  Repeat ↑
 Path
```

## File Dependencies

```
graph.py (BASE)
    │
    ├── Provides: Grid3DPathGraph
    │
    ├─→ astar.py
    │       └── Uses: Grid3DPathGraph
    │       └── Provides: CostAStarSearcher
    │
    └─→ eda_costastar.py
            └── Uses: Grid3DPathGraph + CostAStarSearcher
            └── Provides: EDACostAStarSearcher
```

## Method Organization

### graph.py (233 lines)

```
Node Indexing (4 methods)
├── is_within_bounds()
├── index()
└── unpack_index()

Spatial Operations (3 methods)
├── centroid()
├── neighbor_indices()
└── node_centroid_sequence()

Edge Costs (4 methods)
├── transition_vector()
├── transition_distance()
├── is_safe_transition()
└── transition_cost()

Utilities (1 method)
└── find_neighbors_and_costs()
```

### astar.py (243 lines)

```
Core Algorithm (1 method)
└── search()

Helper Methods (2 methods)
├── _heuristic()
└── _reconstruct_path()

Metrics (1 method)
└── compute_path_metrics()
```

### eda_costastar.py (657 lines)

```
Fitness (1 method)
└── _evaluate_path()

Initialization (1 method)
└── _generate_initial_path()

Probabilistic Model (2 methods)
├── _build_probabilistic_model()
└── _sample_path_from_model()

Mutation (1 method)
└── _mutate_path()

Local Search (1 method)
└── _refine_with_astar()

Main Algorithm (1 method)
└── search()

Utilities (2 methods)
├── _reconstruct_path()
└── compute_path_metrics()
```

## Understanding the Code

### Start Here: graph.py

This is the foundation. It defines:
- How nodes are indexed
- How to find neighbors
- How to compute edge costs

**Key insight**: Everything else builds on this graph structure.

### Then: astar.py

This is the simpler algorithm. It shows:
- How A* works on the graph
- How costs are accumulated
- How paths are reconstructed

**Key insight**: A* explores nodes in order of f_score = g + h.

### Finally: eda_costastar.py

This is the complex algorithm. It combines:
- Evolutionary search (population, selection, mutation)
- Probabilistic modeling (learning from elites)
- A* local search (refinement)

**Key insight**: EDA explores globally, A* refines locally.

## Quick Reference

### Creating a Path

```python
# 1. Create graph
graph = Grid3DPathGraph(grid)

# 2. Choose algorithm
searcher = CostAStarSearcher(graph)  # Fast
# or
searcher = EDACostAStarSearcher(graph)  # Better quality

# 3. Find path
path = searcher.search(
    start_layer, start_row, start_col,
    goal_layer, goal_row, goal_col,
    cost_map
)

# 4. Get coordinates
centroids = graph.node_centroid_sequence(path)
```

### Key Parameters

**Grid3DPathGraph**:
- `safe_separation`: Min distance between waypoints
- `vertical_transition_cost`: Altitude change penalty

**CostAStarSearcher**:
- No parameters (uses graph defaults)

**EDACostAStarSearcher**:
- `population_size`: Number of candidate paths
- `elite_size`: Top solutions for model building
- `max_generations`: Evolution iterations
- `mutation_rate`: Probability of mutation

## Summary

- **graph.py**: The structure (WHAT we search on)
- **astar.py**: Simple algorithm (HOW to search fast)
- **eda_costastar.py**: Complex algorithm (HOW to search well)

Each file has a single responsibility, making it easier to:
- ✅ Understand
- ✅ Modify
- ✅ Test
- ✅ Debug
