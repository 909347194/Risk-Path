# 实验脚本API兼容性检查报告

**检查时间**: 2026-04-27  
**状态**: ⚠️ **严重API不兼容**

---

## 🔴 核心问题

所有实验脚本（experiment_01-04）都存在严重的API不兼容问题。脚本使用的是**假设的API**，与实际的代码实现完全不匹配。

---

## 📋 主要API差异

### 1. Grid3D 构造函数 ✅ 已修正

**修正前（错误）**:
```python
grid = Grid3D(
    bounds=bounds,
    cell_size=80.0,
    layers=[30.0, 60.0, 90.0, 120.0]
)
```

**修正后（正确）**:
```python
minx, miny, maxx, maxy = 12611318, 2640629, 12617018, 2646395
grid = Grid3D(
    minx=minx,
    miny=miny,
    maxx=maxx,
    maxy=maxy,
    cell_size=80.0,
    layer_altitudes=[30.0, 60.0, 90.0, 120.0]
)
```

---

### 2. Grid3D.get_dimensions() ❌ 不存在

**问题**: [Grid3D](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\grid_model.py#L42-L67) 类没有 `get_dimensions()` 方法

**实际属性**:
- `grid.width` - 网格宽度（单元格数）
- `grid.height` - 网格高度（单元格数）
- `grid.layer_altitudes` - 层高度数组

**建议修改**:
```python
# 替换
print(f"  ✓ Grid created: {grid.get_dimensions()}")

# 为
print(f"  ✓ Grid created: {grid.width}x{grid.height} cells, {len(grid.layer_altitudes)} layers")
```

---

### 3. IntegratedCostModel API ❌ 完全错误

**问题**: 实验脚本中的调用方式与实际实现不匹配

**脚本中的调用**:
```python
cost_model = IntegratedCostModel(
    grid=grid,
    population_raster=None,  # ❌ 应该是 Path 类型
    buildings=[]             # ❌ 应该是 GeoDataFrame
)
cost_map = cost_model.compute_layer_costs()  # ❌ 方法不存在
```

**实际API需要调查**: 需要查看 [IntegratedCostModel](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py) 的真实构造函数和方法

---

### 4. Grid3DPathGraph API ❌ 完全错误

**问题**: 
- 构造函数不接受 `clearance` 参数
- 没有 `build_graph()` 方法
- 没有 `num_nodes` 属性

**脚本中的调用**:
```python
graph = Grid3DPathGraph(grid, cost_map, clearance=5.0)  # ❌
graph.build_graph()                                      # ❌
print(f"  ✓ Graph built with {graph.num_nodes} nodes")   # ❌
```

---

### 5. CostAStarSearcher.search() ❌ 参数错误

**问题**: search方法需要详细的坐标参数，而不是简单的元组

**脚本中的调用**:
```python
path, total_cost = searcher.search(start, goal)  # ❌ start和goal是元组
```

**实际签名** (根据之前的检查):
```python
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
```

---

### 6. EDACostAStarSearcher.search() ❌ 返回值错误

**问题**: 
- 只返回路径索引列表，不返回 `(path, cost, metrics)`
- 需要手动转换和计算

**脚本中的期望**:
```python
path, total_cost, metrics = searcher.search(start, goal)  # ❌
```

**实际返回**:
```python
path_indices = searcher.search(...)  # List[int] 或 None
```

---

## 🎯 根本原因分析

### 1. 实验脚本是模板/占位符
这些实验脚本似乎是**基于假设API编写的模板**，而非基于实际实现的代码。

### 2. 缺少实际数据加载逻辑
脚本中有TODO注释：
```python
population_raster = None  # TODO: Load actual population data
buildings = []            # TODO: Load actual building data
```

这表明脚本尚未完成。

### 3. API设计与实现脱节
- 脚本设计者可能参考了论文或设计文档
- 但实际实现时API发生了变化
- 两者未同步更新

---

## 💡 解决方案建议

### 方案A: 重写实验脚本（推荐）⭐

**步骤**:
1. 先研究现有的测试脚本（如 `tests/test_fatality_risk.py`）
2. 了解真实的API使用方式
3. 基于真实API重写实验脚本
4. 添加完整的数据加载逻辑

**优点**:
- ✅ 确保代码可运行
- ✅ 符合项目规范
- ✅ 可作为后续开发的参考

**缺点**:
- ⏰ 需要较多时间

---

### 方案B: 修复现有脚本

**步骤**:
1. 逐个修正API调用
2. 补充缺失的数据加载逻辑
3. 调整返回值处理

**优点**:
- ✅ 保留原有结构

**缺点**:
- ❌ 工作量大
- ❌ 容易遗漏细节
- ❌ 可能需要大幅重构

---

### 方案C: 创建简化版实验脚本（快速验证）

**步骤**:
1. 创建最小化的实验脚本
2. 仅验证核心算法流程
3. 逐步完善功能

**示例**:
```python
"""Minimal experiment to verify algorithm works."""
from core import Grid3D

# Test Grid3D creation
grid = Grid3D(
    minx=12611318, miny=2640629,
    maxx=12617018, maxy=2646395,
    cell_size=80.0,
    layer_altitudes=[30.0, 60.0, 90.0, 120.0]
)
print(f"✓ Grid: {grid.width}x{grid.height}")
```

---

## 📝 下一步行动

### 立即执行:
1. ✅ 修正 Grid3D 构造函数调用（已完成）
2. ⏳ 调查 IntegratedCostModel 的真实API
3. ⏳ 调查 Grid3DPathGraph 的真实API
4. ⏳ 调查各Searcher的真实API

### 短期计划:
1. 选择方案A或C
2. 创建可运行的最小实验脚本
3. 验证算法流程

### 长期计划:
1. 完善数据加载逻辑
2. 添加完整的可视化
3. 编写详细文档

---

## 🔍 需要调查的核心API

| 类/模块 | 需要确认的内容 | 优先级 |
|---------|--------------|--------|
| [IntegratedCostModel](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py) | 构造函数参数、计算方法 | 🔴 高 |
| [Grid3DPathGraph](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py) | 构造函数、图构建方法 | 🔴 高 |
| [CostAStarSearcher](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\astar.py) | search方法签名、返回值 | 🔴 高 |
| [EDACostAStarSearcher](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py) | search方法签名、返回值 | 🔴 高 |
| [TwoStageEDACostAStarSearcher](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\two_stage_eda_costastar.py) | search方法签名、返回值 | 🔴 高 |

---

**总结**: 实验脚本需要大幅重构才能正常运行。建议采用方案A（重写）或方案C（简化版），基于真实API创建可用的实验脚本。

---

**最后更新**: 2026-04-27  
**检查执行人**: AI Code Assistant
