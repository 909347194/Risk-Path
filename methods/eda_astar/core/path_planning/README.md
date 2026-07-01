# Path Planning Module

This module implements path planning algorithms for 3D UAV navigation.

## Module Structure

```
path_planning/
├── __init__.py              # Package exports
├── graph.py                 # 3D graph structure
├── astar.py                 # Cost A* algorithm
├── eda_costastar.py         # EDA-CostA* hybrid algorithm
└── path_graph.py            # DEPRECATED (backward compatibility)
```

## Components

### 1. Graph Structure (`graph.py`)

**Class**: `Grid3DPathGraph`

**Purpose**: Builds and manages the 3D navigation graph

**Key Responsibilities**:
- Node indexing (3D coordinates ↔ linear index)
- Neighbor discovery (26-connectivity)
- Edge cost computation (distance + risk + vertical)
- Spatial operations (centroids, distances)

**Usage**:
```python
from path_planning import Grid3DPathGraph

graph = Grid3DPathGraph(
    grid=grid,
    safe_separation=40.0,
    vertical_transition_cost=1.5
)

# Get neighbors
neighbors = graph.neighbor_indices(layer, row, col)

# Compute edge cost
cost = graph.transition_cost(from_node, to_node, cost_map)
```

### 2. Cost A* Algorithm (`astar.py`)

**Class**: `CostAStarSearcher`

**Purpose**: Deterministic heuristic search for optimal paths

**Algorithm Type**: Greedy, deterministic

**Best For**: 
- Simple risk landscapes
- Fast path finding
- Baseline comparison

**Usage**:
```python
from path_planning import CostAStarSearcher

searcher = CostAStarSearcher(graph)

path = searcher.search(
    start_layer=0, start_row=0, start_col=0,
    goal_layer=3, goal_row=99, goal_col=99,
    cost_map=costs["total"],
    risk_weight=1.0,
    distance_weight=1.0
)
```

**How it Works**:
1. Initialize priority queue with start node
2. Pop node with lowest f_score (g + h)
3. Expand neighbors
4. Update costs if better path found
5. Repeat until goal reached

### 3. EDA-CostA* Algorithm (`eda_costastar.py`)

**Class**: `EDACostAStarSearcher`

**Purpose**: Evolutionary optimization with A* local search

**Algorithm Type**: Stochastic, population-based

**Best For**:
- Complex risk landscapes
- Escaping local optima
- Finding diverse solutions

**Usage**:
```python
from path_planning import EDACostAStarSearcher

searcher = EDACostAStarSearcher(
    graph=graph,
    population_size=50,
    elite_size=10,
    max_generations=100,
    mutation_rate=0.2
)

path = searcher.search(
    start_layer=0, start_row=0, start_col=0,
    goal_layer=3, goal_row=99, goal_col=99,
    cost_map=costs["total"],
    risk_weight=1.0,
    distance_weight=1.0
)
```

**How it Works**:
1. Initialize population with randomized A*
2. Evaluate fitness (cost + distance)
3. Select elite solutions (top-K)
4. Build probabilistic model from elites
5. Sample new paths from model
6. Apply mutation (replace/remove/insert)
7. Refine with A* local search
8. Repeat until convergence

## Algorithm Comparison

| Feature | Cost A* | EDA-CostA* |
|---------|---------|------------|
| **Type** | Deterministic | Stochastic |
| **Search** | Single path | Population (50) |
| **Speed** | Fast (~1-2s) | Slower (~10-20s) |
| **Local Optima** | Can get stuck | Escapes via mutation |
| **Exploration** | Limited | Extensive |
| **Best For** | Simple scenarios | Complex landscapes |

## Key Concepts

### Node Indexing

Nodes are stored as linear indices but represent 3D coordinates:

```
index = layer * (height * width) + row * width + col
```

Example:
```python
# Convert coordinates to index
node = graph.index(layer=2, row=10, col=15)

# Convert index back to coordinates
layer, row, col = graph.unpack_index(node)
```

### Edge Cost Formula

```
cost = distance_weight × distance + risk_weight × vertex_cost + vertical_cost
```

Where:
- `distance`: Euclidean distance between nodes
- `vertex_cost`: Risk cost from cost map
- `vertical_cost`: Penalty for altitude changes

### Fitness Function (EDA-CostA*)

```
fitness = distance_weight × total_distance + risk_weight × total_cost
```

Lower fitness = better path

## Code Organization

### Why Split the Code?

The original `path_graph.py` contained 780+ lines with 3 major components:
1. Graph structure
2. A* algorithm
3. EDA-CostA* algorithm

**Problems with monolithic file**:
- ❌ Hard to understand (too much code)
- ❌ Difficult to navigate
- ❌ Challenging to maintain
- ❌ Mixed responsibilities

**Benefits of splitting**:
- ✅ Clear boundaries between components
- ✅ Each file has single responsibility
- ✅ Easier to understand algorithms
- ✅ Better for testing and debugging
- ✅ Improved maintainability

### Dependency Graph

```
graph.py (base)
    ↓
astar.py (uses graph)
    ↓
eda_costastar.py (uses graph + astar)
```

## Testing

Run the comparison script to see both algorithms in action:

```bash
python examples/compare_algorithms.py
```

This demonstrates:
- Cost A* finding a path quickly
- EDA-CostA* evolving better solutions over time
- Side-by-side performance metrics

## References

**Paper**: Pang et al. (2022)
- Section 3.2: Cost A* algorithm
- Section 3.3: EDA-CostA* hybrid approach
- Eq. 18-20: Cost functions

## Quick Start

```python
from path_planning import Grid3DPathGraph, EDACostAStarSearcher

# Create graph
graph = Grid3DPathGraph(grid)

# Create searcher
searcher = EDACostAStarSearcher(graph)

# Find path
path = searcher.search(
    start_layer=0, start_row=0, start_col=0,
    goal_layer=3, goal_row=99, goal_col=99,
    cost_map=costs["total"]
)

# Get 3D coordinates
centroids = graph.node_centroid_sequence(path)
```
