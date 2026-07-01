# 时空异质性路径规划 - 状态向量设计集成指南

## 概述

本文档说明如何将导师建议的严谨状态向量设计方案集成到 `spatiotemporal_heterogeneity` 项目中。该设计实现了基于论文公式的多维风险累积模型，支持硬约束剪枝和多目标优化。

## 核心设计理念

### 1. 状态向量结构 (`SearchNode`)

每个搜索节点包含完整的物理状态信息：

```python
class SearchNode:
    def __init__(self, x, y, z, t, state_vector, parent=None):
        # 1. 时空坐标：绝对不可分离的4D定位
        self.coords = (x, y, z, t) 
        
        # 2. 状态向量字典：记录各种维度的物理累积量
        self.state = {
            'cum_distance': 0.0,      # 累计飞行距离 (m)
            'cum_time': 0.0,          # 累计飞行时间 (s) -> 决定电池消耗
            'p_survival': 1.0,        # 存活概率 (1.0表示100%存活) -> 乘法累积
            'cum_fatality': 0.0,      # 累计致命风险 (预期致死人数)
            'cum_property': 0.0,      # 累计财产损失成本
            'cum_noise': 0.0          # 累计社会噪音滋扰代价
        }
        
        # 3. 算法寻优变量 (A* 必备)
        self.g = 0.0  # 起点到当前点的加权综合代价
        self.f = 0.0  # f = g + h (启发式总代价)
        
        # 4. 指针
        self.parent = parent
```

**关键特性**：
- ✅ 已实现在 [`common.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\common.py)
- ✅ 符合项目架构规范
- ✅ 支持多维度风险独立追踪

### 2. 环境张量容器 (`EnvTensor`)

提供对独立风险分量张量的统一访问接口：

```python
class EnvTensor:
    """Container for individual 4D risk tensors"""
    
    def __init__(self, p_crash, fatality, property, noise, obstacle=None):
        self.p_crash = p_crash      # 4D: (nx, ny, nz, nt) - 动态坠机概率
        self.fatality = fatality    # 4D: (nx, ny, nz, nt) - 致死率（结合人口潮汐）
        self.property = property    # 3D/4D - 财产风险（静态或动态）
        self.noise = noise          # 4D: (nx, ny, nz, nt) - 噪音代价（昼夜惩罚）
        self.obstacle = obstacle    # 4D binary - 障碍物掩码（可选）
```

**设计优势**：
- 🔹 算法直接访问独立风险分量，而非预组合的 `Cost_total`
- 🔹 支持灵活的多目标权重配置
- 🔹 符合分层架构：`tensor_engine` → `algorithms`

### 3. 节点扩展核心逻辑

这是论文第三章算法部分的核心实现：

```python
def _expand_node(self, current_node, neighbor_coords, dist):
    x1, y1, z1, t1 = current_node.coords
    x2, y2, z2 = neighbor_coords
    
    # --- 1. 计算时间流逝 (Time Progression) ---
    dt = dist / self.uav_speed              # 飞行所需时间
    t2_continuous = current_node.state['cum_time'] + dt
    t2_idx = int(t2_continuous / self.time_resolution)
    
    # --- 2. 提取B点在此刻的各项物理风险属性 ---
    p_crash_local = self.env_tensor.p_crash[x2, y2, z2, t2_idx]
    fatality_local = self.env_tensor.fatality[x2, y2, z2, t2_idx]
    property_local = self.env_tensor.property[x2, y2, z2, ...]
    noise_local = self.env_tensor.noise[x2, y2, z2, t2_idx]
    
    # --- 3. 更新状态向量 (State Vector Update) ---
    new_state = {}
    new_state['cum_distance'] = current_node.state['cum_distance'] + dist
    new_state['cum_time'] = current_node.state['cum_time'] + dt
    
    # 【核心！】存活概率是乘法关系
    new_state['p_survival'] = current_node.state['p_survival'] * (1.0 - p_crash_local)
    
    # 致死、财产、噪音风险是期望的累加（考虑当前存活率）
    new_state['cum_fatality'] = current_node.state['cum_fatality'] + \
                                (current_node.state['p_survival'] * fatality_local * dt)
    new_state['cum_property'] = current_node.state['cum_property'] + \
                                (current_node.state['p_survival'] * property_local * dt)
    new_state['cum_noise'] = current_node.state['cum_noise'] + (noise_local * dt)
    
    # --- 4. 硬约束剪枝 (Hard Constraints Pruning) ---
    if new_state['p_survival'] < self.survival_threshold:
        return None  # 熔断禁飞
    if new_state['cum_time'] > self.max_battery_time:
        return None  # 电池耗尽
        
    # --- 5. 计算综合代价值 g(n) ---
    g_new = (self.w_fatality * new_state['cum_fatality'] + 
             self.w_property * new_state['cum_property'] + 
             self.w_noise * new_state['cum_noise'])
    
    return SearchNode(x2, y2, z2, t2_idx, state_dict=new_state, parent=current_node)
```

**数学对应关系**：
- 📐 **存活概率**: `P_survival = ∏(1 - P_crash)` → 乘法累积
- 📐 **致死风险**: `E[Fatality] = P_survival × Fatality_rate × Δt` → 期望值累加
- 📐 **财产风险**: 同理，考虑存活率的期望损失
- 📐 **噪音成本**: `Noise = ∫ Noise_rate dt` → 时间积分

## 集成步骤

### Step 1: 创建 EnvTensor 模块 ✅

文件位置: [`env_tensor.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\env_tensor.py)

已完成，包含：
- `EnvTensor` 类：封装独立风险张量
- `EnvTensorBuilder` 类：构建器模式组装张量
- `create_env_tensor_from_components()` 便捷函数

### Step 2: 更新 A* 算法 ✅

文件位置: [`astar_4d.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\a_star\astar_4d.py)

主要变更：
1. **构造函数**: 接收 `EnvTensor` 而非 `cost_tensor`
2. **邻居生成**: `_get_neighbors()` 返回 3D 空间邻居，时间动态计算
3. **节点扩展**: `_expand_node()` 实现导师建议的完整逻辑
4. **搜索主循环**: 使用新的扩展方法，支持硬约束剪枝

### Step 3: 从 Tensor Engine 提取组件

#### 方法 A: 直接使用现有张量

如果你的 `tensor_engine` 已经生成了独立的 4D 张量：

```python
from tensor_engine.grid_system import get_macro_grid
from tensor_engine.dynamic_p_crash import DynamicCrashProbability
from tensor_engine.dynamic_population import DynamicPopulationBuilder
from tensor_engine.dynamic_noise import DynamicNoiseBuilder
from algorithms.env_tensor import EnvTensor

# 1. 创建网格
grid = get_macro_grid()

# 2. 构建各个风险分量
crash_model = DynamicCrashProbability(config_path='configs/risk_params.yaml')
p_crash = crash_model.compute(...)  # 根据你的实际API调用

pop_builder = DynamicPopulationBuilder(config)
fatality = pop_builder.build_fatality_tensor()  # 假设的方法

noise_builder = DynamicNoiseBuilder(config)
noise = noise_builder.build_noise_tensor()

property_risk = ...  # 从 static_obstacle 或其他模块获取

# 3. 组装 EnvTensor
env_tensor = EnvTensor(
    p_crash=p_crash,
    fatality=fatality,
    property=property_risk,
    noise=noise
)
```

#### 方法 B: 使用 Builder 模式

```python
from algorithms.env_tensor import EnvTensorBuilder

builder = EnvTensorBuilder(grid)
builder.add_component('p_crash', p_crash)
builder.add_component('fatality', fatality)
builder.add_component('property', property_risk)
builder.add_component('noise', noise)
builder.add_component('obstacle', obstacle)  # 可选

env_tensor = builder.build()
```

### Step 4: 配置加载

从 YAML 配置文件读取参数：

```python
from tensor_engine.load_config import load_config

# 加载配置
env_config = load_config('env_config.yaml')
risk_params = load_config('risk_params.yaml')
cost_weights = load_config('cost_weight.yaml')

# 组装 A* 配置
config = {
    'uav_speed': env_config.uav_speed,
    'time_resolution': env_config.time_step,
    'w_fatality': cost_weights.fatality,
    'w_property': cost_weights.property,
    'w_noise': cost_weights.noise,
    'survival_threshold': risk_params.survival_threshold,
    'max_battery_time': env_config.max_battery_time
}
```

### Step 5: 运行路径规划

```python
from algorithms.a_star.astar_4d import AStar4D

# 初始化规划器
planner = AStar4D(grid, env_tensor, config)

# 定义起点和终点
start = (x1, y1, z1, t1)  # 4D 起点
goal = (x2, y2, z2)       # 3D 终点

# 执行搜索
result = planner.search(start, goal)

# 处理结果
if result['status'] == 'success':
    print(f"路径长度: {len(result['path'])} 个航点")
    print(f"总距离: {result['total_distance']:.2f} m")
    print(f"存活概率: {result['final_p_survival']:.4f}")
    print(f"累计致死风险: {result['cum_fatality']:.6f}")
```

## 完整示例

参考 [`integration_example.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\integration_example.py)，演示了从配置加载到路径规划的完整流程。

运行示例：
```bash
cd methods/spatiotemporal_heterogeneity
uv run python src/algorithms/integration_example.py
```

## 与论文模型的对应关系

| 论文章节 | 公式/概念 | 代码实现位置 |
|---------|----------|-------------|
| Chapter 3 | P_crash = 1 - exp(-λ·Φ·Δt) | `tensor_engine/dynamic_p_crash.py` |
| Chapter 3 | 人口潮汐密度 ρ(x,y,t) | `tensor_engine/dynamic_population.py` |
| Chapter 3 | 噪音社会敏感度 N(x,y,z,t) | `tensor_engine/dynamic_noise.py` |
| Chapter 4 | E[Fatality] = P_survival × Fatality_rate × Δt | `astar_4d.py::_expand_node()` |
| Chapter 4 | 多目标加权 g(n) | `astar_4d.py::_expand_node()` |
| Chapter 5 | A* 搜索算法 | `a_star/astar_4d.py::search()` |

## 架构合规性检查

根据 [`PROJECT_SPEC.md`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\PROJECT_SPEC.md)：

✅ **分层架构**: `data_provision` → `tensor_engine` → `algorithms`  
✅ **高度维处理**: 仅在 `tensor_engine` 中扩展 `nz`  
✅ **配置驱动**: 参数从 YAML 读取，不硬编码  
✅ **张量索引**: 直接使用张量索引，不实例化 Point 对象  
✅ **可复现性**: 所有随机模块接受 seed 参数  

## 关键改进点

### 相比旧实现的提升

| 方面 | 旧实现 | 新实现（导师建议） |
|-----|--------|------------------|
| **时间推进** | 固定时间步长 `t+1` | 基于物理距离 `dt = dist/speed` |
| **风险提取** | 单一 `cost_tensor` | 独立分量 `p_crash`, `fatality`, `property`, `noise` |
| **存活概率** | 简化代理 `1 - cost*0.001` | 严格乘法累积 `∏(1 - p_crash)` |
| **风险累积** | 仅累加 `cum_noise` | 分别追踪 `cum_fatality`, `cum_property`, `cum_noise` |
| **硬约束** | 无 | 存活率阈值 + 电池续航检查 |
| **多目标** | 简单加权距离+成本 | 基于各风险分量的加权求和 |

## 常见问题

### Q1: 如何处理 3D 静态属性张量？

`EnvTensor` 支持 `property` 为 3D 或 4D：

```python
if self.env_tensor.property.ndim == 4:
    property_local = self.env_tensor.property[x2, y2, z2, t2_idx]
else:
    property_local = self.env_tensor.property[x2, y2, z2]
```

### Q2: 如何调整多目标权重？

修改 `cost_weight.yaml` 或在代码中设置：

```python
config = {
    'w_fatality': 2.0,   # 提高致死风险权重
    'w_property': 1.0,
    'w_noise': 0.5,      # 降低噪音权重
}
```

### Q3: 如何禁用某些风险维度？

将对应权重设为 0：

```python
config['w_noise'] = 0.0  # 忽略噪音成本
```

### Q4: 如何调试状态向量更新？

在 `_expand_node()` 中添加日志：

```python
print(f"Step: dist={dist:.2f}m, dt={dt:.2f}s")
print(f"  p_crash={p_crash_local:.6f}, survival={new_state['p_survival']:.4f}")
print(f"  fatality={fatality_local:.4f}, cum_fatality={new_state['cum_fatality']:.6f}")
```

## 下一步工作

1. **单元测试**: 为 `_expand_node()` 编写测试用例，验证状态更新逻辑
2. **性能优化**: 考虑使用 NumPy 向量化操作加速批量节点扩展
3. **可视化**: 扩展 `visualization` 模块，展示多维风险沿路径的累积
4. **敏感性分析**: 实验不同权重组合对路径选择的影响
5. **真实数据集成**: 将 `tensor_engine` 的真实 GIS 数据输出连接到 `EnvTensor`

## 参考资料

- [`PROJECT_SPEC.md`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\PROJECT_SPEC.md) - 项目架构规范
- [`common.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\common.py) - SearchNode 定义
- [`env_tensor.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\env_tensor.py) - 环境张量容器
- [`astar_4d.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\a_star\astar_4d.py) - A* 算法实现
- [`integration_example.py`](file://e:\01Reproduction\Risk-Path\methods\spatiotemporal_heterogeneity\src\algorithms\integration_example.py) - 完整集成示例

---

**最后更新**: 2026-05-20  
**作者**: AI Assistant  
**版本**: 1.0
