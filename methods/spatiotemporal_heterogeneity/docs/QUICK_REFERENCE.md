# 快速参考卡 - 状态向量设计集成

## 🎯 核心 API

### 1. 创建 EnvTensor

```python
from algorithms.env_tensor import EnvTensor, create_env_tensor_from_components

# 方法 A: 直接构造
env_tensor = EnvTensor(
    p_crash=p_crash_4d,      # (nx, ny, nz, nt)
    fatality=fatality_4d,    # (nx, ny, nz, nt)
    property=property_risk,  # 3D or 4D
    noise=noise_4d           # (nx, ny, nz, nt)
)

# 方法 B: 便捷函数
env_tensor = create_env_tensor_from_components(
    grid=grid,
    p_crash=p_crash_4d,
    fatality=fatality_4d,
    property_risk=property_risk,
    noise=noise_4d
)
```

### 2. 配置 A* 规划器

```python
from algorithms.a_star.astar_4d import AStar4D

config = {
    'uav_speed': 15.0,              # m/s
    'time_resolution': 3600.0,      # seconds per time slice
    'w_fatality': 1.0,              # 致死风险权重
    'w_property': 1.0,              # 财产风险权重
    'w_noise': 1.0,                 # 噪音成本权重
    'w_distance': 0.0,              # 距离权重（可选）
    'survival_threshold': 0.95,     # 最小存活概率
    'max_battery_time': 3600.0      # 最大飞行时间 (秒)
}

planner = AStar4D(grid, env_tensor, config)
```

### 3. 执行路径搜索

```python
start = (x1, y1, z1, t1)  # 4D 起点
goal = (x2, y2, z2)       # 3D 终点

result = planner.search(start, goal)

if result['status'] == 'success':
    path = result['path']
    total_dist = result['total_distance']
    total_time = result['total_time']
    survival = result['final_p_survival']
    cum_fatality = result['cum_fatality']
    cum_property = result['cum_property']
    cum_noise = result['cum_noise']
```

---

## 🔧 关键参数说明

### UAV 飞行参数

| 参数 | 默认值 | 单位 | 说明 |
|------|--------|------|------|
| `uav_speed` | 15.0 | m/s | 无人机飞行速度，影响时间推进 |
| `time_resolution` | 3600.0 | s | 时间片分辨率，决定 t 索引计算 |

### 多目标权重

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| `w_fatality` | 1.0 | [0, ∞) | 致死风险权重，越高越避开人口密集区 |
| `w_property` | 1.0 | [0, ∞) | 财产损失权重，越高越避开高价值建筑 |
| `w_noise` | 1.0 | [0, ∞) | 噪音滋扰权重，越高越避开敏感区域 |
| `w_distance` | 0.0 | [0, ∞) | 距离权重，通常设为 0 |

**调整建议**:
- 优先安全: `w_fatality=2.0, w_property=1.0, w_noise=0.5`
- 平衡模式: `w_fatality=1.0, w_property=1.0, w_noise=1.0`
- 最短路径: `w_fatality=0.1, w_property=0.1, w_noise=0.1`

### 硬约束

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `survival_threshold` | 0.95 | 低于此存活率的路径被剪枝 |
| `max_battery_time` | 3600.0 | 超过此时间的路径被剪枝 |

**调整建议**:
- 严格安全: `survival_threshold=0.99`
- 标准模式: `survival_threshold=0.95`
- 宽松模式: `survival_threshold=0.90`

---

## 📊 状态向量字段

每个 `SearchNode.state` 包含：

```python
{
    'cum_distance': float,   # 累计飞行距离 (m)
    'cum_time': float,       # 累计飞行时间 (s)
    'p_survival': float,     # 存活概率 [0, 1]
    'cum_fatality': float,   # 累计预期致死人数
    'cum_property': float,   # 累计财产损失成本
    'cum_noise': float       # 累计噪音滋扰代价
}
```

**更新规则**:
- `cum_distance`: 累加 `dist`
- `cum_time`: 累加 `dt = dist / uav_speed`
- `p_survival`: 乘法 `*= (1 - p_crash)`
- `cum_fatality`: 累加 `p_survival × fatality × dt`
- `cum_property`: 累加 `p_survival × property × dt`
- `cum_noise`: 累加 `noise × dt`

---

## 🐛 常见问题排查

### Q1: 路径搜索失败（返回 `None`）

**可能原因**:
1. 起点或终点在障碍物内
2. 存活率阈值过高，所有路径都被剪枝
3. 电池续航时间过短

**解决方法**:
```python
# 降低存活率阈值
config['survival_threshold'] = 0.90

# 增加电池续航
config['max_battery_time'] = 7200.0

# 检查障碍物
print(f"Obstacle cells: {np.sum(env_tensor.obstacle > 0.5)}")
```

### Q2: 计算时间过长

**可能原因**:
1. 网格规模过大
2. 启发式函数不够准确

**解决方法**:
```python
# 使用更小的网格
grid = get_micro_grid()  # 而非 macro_grid

# 调整权重以加速收敛
config['w_distance'] = 0.1  # 添加距离启发
```

### Q3: 张量维度不匹配

**错误信息**: `ValueError: Inconsistent spatial dimensions`

**解决方法**:
```python
# 检查各张量形状
print(f"p_crash shape: {p_crash.shape}")
print(f"fatality shape: {fatality.shape}")
print(f"property shape: {property.shape}")
print(f"noise shape: {noise.shape}")

# 确保空间维度一致 (nx, ny, nz)
assert p_crash.shape[:3] == fatality.shape[:3]
assert p_crash.shape[:3] == noise.shape[:3]
```

### Q4: 存活概率下降过快

**可能原因**: `p_crash` 值过高

**解决方法**:
```python
# 检查 p_crash 范围
print(f"p_crash range: [{p_crash.min()}, {p_crash.max()}]")
print(f"p_crash mean: {p_crash.mean()}")

# 正常范围应该是 1e-6 到 1e-3
# 如果过大，检查 tensor_engine 的参数配置
```

---

## 📁 文件位置速查

| 功能 | 文件路径 |
|------|---------|
| SearchNode 定义 | `src/algorithms/common.py` |
| EnvTensor 容器 | `src/algorithms/env_tensor.py` |
| A* 算法实现 | `src/algorithms/a_star/astar_4d.py` |
| 集成示例 | `src/algorithms/integration_example.py` |
| 集成指南 | `INTEGRATION_GUIDE.md` |
| 完成总结 | `COMPLETION_SUMMARY.md` |
| 项目规范 | `PROJECT_SPEC.md` |
| 配置文件 | `configs/*.yaml` |

---

## 🚀 一键运行示例

```bash
# 进入项目目录
cd methods/spatiotemporal_heterogeneity

# 运行集成示例
uv run python src/algorithms/integration_example.py

# 运行 A* 单元测试
uv run python src/algorithms/a_star/astar_4d.py
```

---

## 📖 相关文档链接

- [完整集成指南](INTEGRATION_GUIDE.md) - 详细步骤和理论解释
- [完成总结](COMPLETION_SUMMARY.md) - 已完成工作和下一步计划
- [项目规范](PROJECT_SPEC.md) - 架构设计和数据流

---

**最后更新**: 2026-05-20  
**版本**: 1.0  
**维护者**: AI Assistant
