# API 参考手册

**版本**: 1.0  
**最后更新**: 2026-04-27

---

## 📋 目录

1. [核心模块概览](#核心模块概览)
2. [风险模型 API](#风险模型-api)
3. [路径规划 API](#路径规划-api)
4. [可视化工具 API](#可视化工具-api)
5. [使用示例](#使用示例)

---

## 核心模块概览

### 模块结构

```
core/
├── risk_model/          # 风险建模
│   ├── fatality_risk.py
│   ├── traffic_risk.py
│   ├── property_risk.py
│   ├── noise_risk.py
│   └── cost_model.py
│
└── path_planning/       # 路径规划
    ├── graph.py
    ├── astar.py
    ├── enhanced_astar.py
    ├── eda_costastar.py
    ├── two_stage_eda_costastar.py
    ├── clustering.py
    └── heuristic_calculator.py
```

### 快速导入

```python
# 方式1: 统一API（推荐）
from core import (
    Grid3D,
    IntegratedCostModel,
    TwoStageEDACostAStarSearcher,
)

# 方式2: 直接导入子模块
from core.risk_model import FatalityRiskModel
from core.path_planning import CostAStarSearcher
```

---

## 风险模型 API

### Grid3D - 3D网格环境

**文件**: [`core/risk_model/grid_model.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\grid_model.py)

#### 构造函数

```python
class Grid3D:
    def __init__(
        self,
        bounds: Tuple[float, float, float, float],  # (xmin, ymin, xmax, ymax)
        cell_size: float = 80.0,                     # 单元格大小（米）
        layers: List[float] = [30.0, 60.0, 90.0, 120.0],  # 高度层
        padding: float = 160.0                       # 边界填充
    )
```

#### 主要方法

```python
# 获取网格维度
grid.get_dimensions() -> Tuple[int, int, int]  # (n_layers, n_rows, n_cols)

# 坐标转换
grid.world_to_grid(x: float, y: float) -> Tuple[int, int]
grid.grid_to_world(row: int, col: int) -> Tuple[float, float]

# 加载建筑物数据
grid.load_buildings(shapefile_path: str) -> None

# 检查碰撞
grid.is_obstacle(layer: int, row: int, col: int) -> bool
```

#### 使用示例

```python
from core.risk_model import Grid3D

# 创建网格
bounds = (12611318, 2640629, 12617018, 2646395)
grid = Grid3D(
    bounds=bounds,
    cell_size=80.0,
    layers=[30.0, 60.0, 90.0, 120.0]
)

print(f"Grid dimensions: {grid.get_dimensions()}")
# Output: Grid dimensions: (4, 73, 72)
```

---

### FatalityRiskModel - 致死风险模型

**文件**: [`core/risk_model/fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py)

#### 构造函数

```python
class FatalityRiskModel:
    def __init__(
        self,
        grid: Grid3D,
        population_raster: np.ndarray,
        uav_mass: float = 25.0,      # UAV质量（kg）
        crash_probability: float = 1e-4  # 基础碰撞概率
    )
```

#### 主要方法

```python
# 计算致死风险地图
model.compute_risk_map() -> np.ndarray  # Shape: (n_layers, n_rows, n_cols)

# 计算单个单元格的致死风险
model.compute_cell_risk(
    layer: int,
    row: int,
    col: int,
    height: float
) -> float

# 获取行人致死率
model.calculate_pedestrian_fatality(
    kinetic_energy: float,
    pop_density: float
) -> float

# 获取车辆致死率
model.calculate_vehicle_fatality(
    kinetic_energy: float,
    traffic_density: float
) -> float
```

#### 使用示例

```python
from core.risk_model import Grid3D, FatalityRiskModel

# 初始化
grid = Grid3D(bounds, cell_size=80.0, layers=[30, 60, 90, 120])
pop_raster = load_population_data()  # 自定义数据加载函数

model = FatalityRiskModel(
    grid=grid,
    population_raster=pop_raster,
    uav_mass=25.0
)

# 计算风险地图
risk_map = model.compute_risk_map()
print(f"Risk map shape: {risk_map.shape}")
print(f"Max risk: {risk_map.max():.6f}")
```

---

### PropertyDamageRiskModel - 财产损失风险模型

**文件**: [`core/risk_model/property_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\property_risk.py)

#### 构造函数

```python
class PropertyDamageRiskModel:
    def __init__(
        self,
        grid: Grid3D,
        buildings: List[Building],
        mu: float = 4.0,      # 建筑高度对数均值
        sigma: float = 0.8    # 建筑高度对数标准差
    )
```

#### 主要方法

```python
# 计算财产风险地图
model.compute_risk_map() -> np.ndarray

# 计算对数正态分布PDF
model.lognormal_pdf(h: float, mu: float, sigma: float) -> float

# 获取单个单元格风险
model.compute_cell_risk(
    layer: int,
    row: int,
    col: int
) -> float
```

---

### NoiseRiskModel - 噪声风险模型

**文件**: [`core/risk_model/noise_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\noise_risk.py)

#### 构造函数

```python
class NoiseRiskModel:
    def __init__(
        self,
        grid: Grid3D,
        L_0: float = 80.0,     # 参考高度噪声级（dB）
        h_0: float = 10.0,     # 参考高度（m）
        varpi: float = 0.5     # 噪声权重系数
    )
```

#### 主要方法

```python
# 计算噪声风险地图
model.compute_risk_map() -> np.ndarray

# 计算噪声影响
model.compute_noise_impact(
    height: float,
    horizontal_distance: float
) -> float

# 计算声压级衰减
model.compute_sound_level(height: float) -> float
```

---

### TrafficRiskModel - 交通风险模型

**文件**: [`core/risk_model/traffic_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\traffic_risk.py)

#### 构造函数

```python
class TrafficRiskModel:
    def __init__(
        self,
        grid: Grid3D,
        road_density_raster: np.ndarray,
        population_raster: np.ndarray,
        weight: float = 1.0
    )
```

#### 主要方法

```python
# 计算交通风险地图
model.compute_risk_map() -> np.ndarray

# 计算单个单元格风险
model.compute_traffic_risk(
    road_density: float,
    population_density: float
) -> float
```

---

### IntegratedCostModel - 集成成本模型

**文件**: [`core/risk_model/cost_model.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py)

#### 构造函数

```python
class IntegratedCostModel:
    def __init__(
        self,
        grid: Grid3D,
        population_raster: np.ndarray,
        buildings: List[Building],
        weights: Dict[str, float] = {
            'fatality': 1.0,
            'property': 0.8,
            'noise': 0.6,
            'traffic': 0.5,
            'distance': 1.0
        }
    )
```

#### 主要方法

```python
# 计算集成成本地图（核心方法）
model.compute_layer_costs() -> np.ndarray  # Shape: (n_layers, n_rows, n_cols)

# 计算单个单元格的综合成本
model.compute_integrated_cost(
    layer: int,
    row: int,
    col: int,
    risk_components: Dict[str, float]
) -> float

# 归一化风险分量
model.normalize_risk_component(
    risk_values: np.ndarray,
    risk_type: str
) -> np.ndarray
```

#### 使用示例

```python
from core.risk_model import Grid3D, IntegratedCostModel

# 初始化
grid = Grid3D(bounds, cell_size=80.0, layers=[30, 60, 90, 120])
pop_raster = load_population_data()
buildings = load_buildings()

cost_model = IntegratedCostModel(
    grid=grid,
    population_raster=pop_raster,
    buildings=buildings,
    weights={
        'fatality': 1.0,
        'property': 0.8,
        'noise': 0.6,
        'traffic': 0.5,
        'distance': 1.0
    }
)

# 计算成本地图
cost_map = cost_model.compute_layer_costs()
print(f"Cost map shape: {cost_map.shape}")
print(f"Cost range: [{cost_map.min():.2f}, {cost_map.max():.2f}]")
```

---

## 路径规划 API

### Grid3DPathGraph - 3D路径图

**文件**: [`core/path_planning/graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py)

#### 构造函数

```python
class Grid3DPathGraph:
    def __init__(
        self,
        grid: Grid3D,
        cost_map: np.ndarray,
        clearance: float = 5.0  # 最小安全距离
    )
```

#### 主要方法

```python
# 构建图结构
graph.build_graph() -> None

# 获取邻居节点（26邻域）
graph.get_neighbors(
    layer: int,
    row: int,
    col: int
) -> List[Tuple[int, int, int]]

# 获取边成本
graph.get_edge_cost(
    node1: Tuple[int, int, int],
    node2: Tuple[int, int, int]
) -> float

# 检查节点有效性
graph.is_valid_node(
    layer: int,
    row: int,
    col: int
) -> bool
```

---

### CostAStarSearcher - 标准Cost A*

**文件**: [`core/path_planning/astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\astar.py)

#### 构造函数

```python
class CostAStarSearcher:
    def __init__(
        self,
        graph: Grid3DPathGraph,
        heuristic_type: str = 'euclidean'  # 'euclidean' or 'manhattan'
    )
```

#### 主要方法

```python
# 搜索最优路径（核心方法）
searcher.search(
    start: Tuple[int, int, int],  # (layer, row, col)
    goal: Tuple[int, int, int]
) -> Tuple[List[Tuple[int, int, int]], float]
# Returns: (path, total_cost)

# 获取搜索统计信息
searcher.get_search_stats() -> Dict[str, any]
# Returns: {'iterations': int, 'open_set_size': int, ...}
```

#### 使用示例

```python
from core.path_planning import Grid3DPathGraph, CostAStarSearcher

# 构建图
graph = Grid3DPathGraph(grid, cost_map, clearance=5.0)
graph.build_graph()

# 初始化搜索器
searcher = CostAStarSearcher(graph)

# 执行搜索
start = (0, 0, 0)    # Layer 0, Row 0, Col 0
goal = (3, 72, 71)   # Layer 3, Row 72, Col 71

path, total_cost = searcher.search(start, goal)

print(f"Path found with {len(path)} waypoints")
print(f"Total cost: {total_cost:.2f}")
```

---

### EnhancedCostAStarSearcher - 增强Cost A*

**文件**: [`core/path_planning/enhanced_astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\enhanced_astar.py)

#### 构造函数

```python
class EnhancedCostAStarSearcher:
    def __init__(
        self,
        graph: Grid3DPathGraph,
        centroids: List[Tuple[int, int, int]],
        open_costs: np.ndarray,
        epsilon: float = 0.2  # 自适应切换阈值
    )
```

#### 主要方法

```python
# 搜索路径（带自适应启发式）
searcher.search(
    start: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> Tuple[List[Tuple[int, int, int]], float]

# 计算自适应启发式
searcher.adaptive_heuristic(
    current: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> float
```

#### 使用示例

```python
from core.path_planning import EnhancedCostAStarSearcher

# 需要预先计算聚类中心和开放点成本
centroids = [(1, 25, 25), (2, 40, 40), (3, 55, 55)]
open_costs = np.array([...])  # From EDA output

searcher = EnhancedCostAStarSearcher(
    graph=graph,
    centroids=centroids,
    open_costs=open_costs,
    epsilon=0.2
)

path, cost = searcher.search(start, goal)
```

---

### EDACostAStarSearcher - Original EDA-A*

**文件**: [`core/path_planning/eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py)

#### 构造函数

```python
class EDACostAStarSearcher:
    def __init__(
        self,
        graph: Grid3DPathGraph,
        population_size: int = 20,
        elite_size: int = 4,
        max_generations: int = 30,
        learning_rate: float = 0.2
    )
```

#### 主要方法

```python
# 执行EDA优化搜索
searcher.search(
    start: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> Tuple[List[Tuple[int, int, int]], float, Dict]
# Returns: (path, cost, metrics)

# 获取EDA收敛历史
searcher.get_convergence_history() -> List[Dict]
```

#### 使用示例

```python
from core.path_planning import EDACostAStarSearcher

searcher = EDACostAStarSearcher(
    graph=graph,
    population_size=20,
    elite_size=4,
    max_generations=30,
    learning_rate=0.2
)

path, cost, metrics = searcher.search(start, goal)

print(f"EDA converged in {metrics['generations']} generations")
print(f"Best fitness: {metrics['best_fitness']:.2f}")
```

---

### TwoStageEDACostAStarSearcher - Two-Stage EDA-CostA* ⭐

**文件**: [`core/path_planning/two_stage_eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\two_stage_eda_costastar.py)

#### 构造函数

```python
class TwoStageEDACostAStarSearcher:
    def __init__(
        self,
        graph: Grid3DPathGraph,
        cost_map: np.ndarray,
        eda_params: Dict = {
            'population_size': 20,
            'elite_size': 4,
            'max_generations': 30,
            'learning_rate': 0.2
        },
        clustering_params: Dict = {
            'n_clusters': 5
        },
        epsilon: float = 0.2
    )
```

#### 主要方法

```python
# 执行两阶段搜索（核心方法）
searcher.search(
    start: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> Tuple[List[Tuple[int, int, int]], float, Dict]
# Returns: (path, cost, detailed_metrics)

# Stage 1: EDA优化
searcher.stage1_eda_optimization(
    start: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> Tuple[np.ndarray, Dict]
# Returns: (best_region_mask, eda_metrics)

# Stage 2: 提取开放点并聚类
searcher.stage2_clustering(
    best_region: set
) -> Tuple[List[Tuple], List[Tuple]]
# Returns: (open_points, centroids)

# Stage 3: 增强CostA*搜索
searcher.stage3_enhanced_search(
    start: Tuple[int, int, int],
    goal: Tuple[int, int, int],
    centroids: List[Tuple],
    open_costs: np.ndarray
) -> Tuple[List[Tuple], float]
```

#### 使用示例

```python
from core.path_planning import TwoStageEDACostAStarSearcher

# 初始化
searcher = TwoStageEDACostAStarSearcher(
    graph=graph,
    cost_map=cost_map,
    eda_params={
        'population_size': 20,
        'elite_size': 4,
        'max_generations': 30,
        'learning_rate': 0.2
    },
    clustering_params={'n_clusters': 5},
    epsilon=0.2
)

# 执行搜索
start = (0, 0, 0)
goal = (3, 72, 71)

path, cost, metrics = searcher.search(start, goal)

# 查看详细指标
print(f"Stage 1 - EDA generations: {metrics['eda']['generations']}")
print(f"Stage 2 - Clusters: {len(metrics['clustering']['centroids'])}")
print(f"Stage 3 - A* iterations: {metrics['enhanced_astar']['iterations']}")
print(f"Final cost: {cost:.2f}")
```

---

### KMeansClusterer - K-means聚类

**文件**: [`core/path_planning/clustering.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\clustering.py)

#### 构造函数

```python
class KMeansClusterer:
    def __init__(
        self,
        n_clusters: int = 5,
        max_iterations: int = 100,
        tolerance: float = 1e-4
    )
```

#### 主要方法

```python
# 执行聚类
clusterer.cluster(
    points: List[Tuple[int, int, int]],
    use_physical_coords: bool = True
) -> Tuple[np.ndarray, List[int]]
# Returns: (centroids, labels)

# 获取聚类结果
clusterer.get_centroids() -> np.ndarray
clusterer.get_labels() -> List[int]
clusterer.get_inertia() -> float
```

---

### AdvancedHeuristicCalculator - 高级启发式计算器

**文件**: [`core/path_planning/heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py)

#### 构造函数

```python
class AdvancedHeuristicCalculator:
    def __init__(
        self,
        centroids: List[Tuple[int, int, int]],
        open_costs: np.ndarray,
        centroid_costs: np.ndarray
    )
```

#### 主要方法

```python
# 计算全局启发式（公式24）
calculator.compute_global_heuristic(
    current: Tuple[int, int, int],
    goal: Tuple[int, int, int]
) -> float

# 计算局部启发式（公式25）
calculator.compute_local_heuristic(
    current: Tuple[int, int, int]
) -> float

# 自适应切换（公式26）
calculator.adaptive_heuristic(
    current: Tuple[int, int, int],
    goal: Tuple[int, int, int],
    epsilon: float = 0.2
) -> float
```

---

## 可视化工具 API

### TwoStageEDAVisualizer - Two-Stage专用可视化

**文件**: [`visualization/two_stage_visualizer.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\visualization\two_stage_visualizer.py)

#### 构造函数

```python
class TwoStageEDAVisualizer:
    def __init__(
        self,
        output_dir: str = "visualizations/two_stage_eda",
        dpi: int = 300
    )
```

#### 主要方法

```python
# 生成EDA收敛曲线
viz.plot_eda_convergence(
    convergence_history: List[Dict],
    save_path: str = "eda_convergence.png"
) -> None

# 生成概率矩阵演化图
viz.plot_probability_matrix_evolution(
    probability_matrices: List[np.ndarray],
    save_path: str = "probability_matrix_evolution.png"
) -> None

# 生成聚类结果图
viz.plot_clustering_results(
    open_points: List[Tuple],
    centroids: List[Tuple],
    labels: List[int],
    save_path: str = "clustering_results.png"
) -> None

# 生成路径对比图
viz.plot_path_comparison(
    paths: Dict[str, List[Tuple]],
    costs: Dict[str, float],
    save_path: str = "path_comparison.png"
) -> None

# 生成成本地图切片
viz.plot_cost_map_slices(
    cost_map: np.ndarray,
    save_path: str = "cost_map_slices.png"
) -> None

# 生成综合报告
viz.generate_comprehensive_report(
    metrics: Dict,
    save_path: str = "comprehensive_report.txt"
) -> None
```

#### 使用示例

```python
from visualization import TwoStageEDAVisualizer

# 初始化
viz = TwoStageEDAVisualizer(output_dir="output/visualizations")

# 生成所有图表
viz.plot_eda_convergence(eda_history)
viz.plot_clustering_results(open_points, centroids, labels)
viz.plot_path_comparison(paths_dict, costs_dict)
viz.plot_cost_map_slices(cost_map)
viz.generate_comprehensive_report(metrics)

print("All visualizations saved!")
```

---

## 使用示例

### 完整流程示例

```python
"""
Complete workflow example for Two-Stage EDA-CostA*
"""

from core import (
    Grid3D,
    IntegratedCostModel,
    TwoStageEDACostAStarSearcher,
)
from visualization import TwoStageEDAVisualizer

# ===== Step 1: Setup Environment =====
print("Setting up environment...")

bounds = (12611318, 2640629, 12617018, 2646395)
grid = Grid3D(
    bounds=bounds,
    cell_size=80.0,
    layers=[30.0, 60.0, 90.0, 120.0]
)

# Load data
population_raster = load_population_data()
buildings = load_buildings()

# ===== Step 2: Compute Cost Map =====
print("Computing integrated cost map...")

cost_model = IntegratedCostModel(
    grid=grid,
    population_raster=population_raster,
    buildings=buildings,
    weights={
        'fatality': 1.0,
        'property': 0.8,
        'noise': 0.6,
        'traffic': 0.5,
        'distance': 1.0
    }
)

cost_map = cost_model.compute_layer_costs()
print(f"Cost map shape: {cost_map.shape}")
print(f"Cost range: [{cost_map.min():.2f}, {cost_map.max():.2f}]")

# ===== Step 3: Build Graph =====
print("Building 3D path graph...")

from core.path_planning import Grid3DPathGraph

graph = Grid3DPathGraph(grid, cost_map, clearance=5.0)
graph.build_graph()
print(f"Graph built with {graph.num_nodes} nodes")

# ===== Step 4: Path Planning =====
print("Running Two-Stage EDA-CostA*...")

searcher = TwoStageEDACostAStarSearcher(
    graph=graph,
    cost_map=cost_map,
    eda_params={
        'population_size': 20,
        'elite_size': 4,
        'max_generations': 30,
        'learning_rate': 0.2
    },
    clustering_params={'n_clusters': 5},
    epsilon=0.2
)

start = (0, 0, 0)
goal = (3, 72, 71)

path, cost, metrics = searcher.search(start, goal)

print(f"\n✓ Path found!")
print(f"  Waypoints: {len(path)}")
print(f"  Total cost: {cost:.2f}")
print(f"  EDA generations: {metrics['eda']['generations']}")
print(f"  Clusters: {len(metrics['clustering']['centroids'])}")
print(f"  A* iterations: {metrics['enhanced_astar']['iterations']}")

# ===== Step 5: Visualization =====
print("\nGenerating visualizations...")

viz = TwoStageEDAVisualizer(output_dir="output/visualizations")

viz.plot_eda_convergence(metrics['eda']['history'])
viz.plot_clustering_results(
    metrics['clustering']['open_points'],
    metrics['clustering']['centroids'],
    metrics['clustering']['labels']
)
viz.plot_path_comparison(
    paths={'Two-Stage EDA': path},
    costs={'Two-Stage EDA': cost}
)
viz.plot_cost_map_slices(cost_map)
viz.generate_comprehensive_report(metrics)

print("✓ All visualizations saved to output/visualizations/")
```

---

### 算法对比示例

```python
"""
Compare three algorithms on the same scenario
"""

from core.path_planning import (
    CostAStarSearcher,
    EDACostAStarSearcher,
    TwoStageEDACostAStarSearcher,
)

# Setup (same as above)
graph = Grid3DPathGraph(grid, cost_map)
graph.build_graph()

start = (0, 0, 0)
goal = (3, 72, 71)

# Algorithm 1: Standard Cost A*
print("Running Standard Cost A*...")
astar = CostAStarSearcher(graph)
path1, cost1 = astar.search(start, goal)

# Algorithm 2: Original EDA-A*
print("Running Original EDA-A*...")
eda = EDACostAStarSearcher(
    graph,
    population_size=20,
    elite_size=4,
    max_generations=30
)
path2, cost2, _ = eda.search(start, goal)

# Algorithm 3: Two-Stage EDA-CostA*
print("Running Two-Stage EDA-CostA*...")
two_stage = TwoStageEDACostAStarSearcher(graph, cost_map)
path3, cost3, _ = two_stage.search(start, goal)

# Comparison
print("\n" + "="*60)
print("Algorithm Comparison Results")
print("="*60)
print(f"{'Algorithm':<25} {'Cost':>10} {'Distance':>12} {'Waypoints':>10}")
print("-"*60)
print(f"{'Standard Cost A*':<25} {cost1:>10.2f} {'N/A':>12} {len(path1):>10}")
print(f"{'Original EDA-A*':<25} {cost2:>10.2f} {'N/A':>12} {len(path2):>10}")
print(f"{'Two-Stage EDA':<25} {cost3:>10.2f} {'N/A':>12} {len(path3):>10}")
print("="*60)
```

---

## 📚 相关文档

- **[ALGORITHMS.md](ALGORITHMS.md)** - 算法完整说明
- **[FORMULAS.md](FORMULAS.md)** - 公式实现对照表
- **[VALIDATION_REPORT.md](VALIDATION_REPORT.md)** - 验证报告

---

**最后更新**: 2026-04-27
