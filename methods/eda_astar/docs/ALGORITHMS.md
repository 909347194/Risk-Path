# EDA-CostA* 算法完整说明

**版本**: 1.0  
**最后更新**: 2026-04-27  
**参考论文**: Pang et al. (2022) - Hybrid EDA-A* algorithm for cost-based path planning

---

## 📋 目录

1. [算法概览](#算法概览)
2. [Algorithm 1: Standard Cost A*](#algorithm-1-standard-cost-a)
3. [Algorithm 2: Original EDA-A*](#algorithm-2-original-eda-a)
4. [Algorithm 3: Two-Stage EDA-CostA*](#algorithm-3-two-stage-eda-costa)
5. [核心公式实现](#核心公式实现)
6. [性能对比](#性能对比)

---

## 算法概览

本项目实现了三种路径规划算法，用于城市环境中的无人机风险规避路径规划：

| 算法 | 特点 | 适用场景 |
|------|------|---------|
| **Standard Cost A*** | 基础成本感知A*搜索 | 基准对比 |
| **Original EDA-A*** | EDA优化搜索区域 + A* | 中等复杂度环境 |
| **Two-Stage EDA-CostA*** | EDA + 聚类 + 自适应启发式 | 复杂城市环境（推荐） |

---

## Algorithm 1: Standard Cost A*

### 核心思想
传统的A*算法扩展，将距离成本替换为集成风险成本。

### 实现位置
[`core/path_planning/astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\astar.py) - `CostAStarSearcher`类

### 算法流程
```python
1. 初始化开放列表（open set）和关闭列表（closed set）
2. 计算起点到所有邻居的成本 g(n) = g(parent) + cost(edge)
3. 启发式估计 h(n) = Euclidean distance to goal
4. f(n) = g(n) + h(n)
5. 选择f值最小的节点扩展
6. 重复直到到达目标或开放列表为空
```

### 关键特性
- ✅ 26邻域移动（3D空间）
- ✅ 碰撞避免（建筑物单元格设为inf）
- ✅ 集成成本模型（公式18-19）

---

## Algorithm 2: Original EDA-A*

### 核心思想
使用估计分布算法（EDA）优化搜索区域，然后在该区域内运行CostA*。

### 实现位置
[`core/path_planning/eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py) - `EDACostAStarSearcher`类

### 算法流程（伪代码）
```
Algorithm 2: EDA-CostA*
Input: Cost map, Start, Goal
Output: Optimal path

1. Initialize probability matrix P (uniform distribution)
2. For generation = 1 to MaxGen:
   a. Sample N individuals from P (Bernoulli sampling)
   b. Evaluate fitness of each individual (run A* in sampled region)
   c. Select elite population Ds (top M individuals)
   d. Update probability matrix:
      P_{i+1} = (1 - α) * P_i + α * mean(Ds)
3. Extract best region from final P
4. Run CostA* in best region
5. Return optimal path
```

### 关键参数
- **Population size (N)**: 20-50
- **Elite size (M)**: 4-10 (通常为N的20%)
- **Learning rate (α)**: 0.1-0.3
- **Max generations**: 30-50

### 优势与局限
✅ **优势**: 
- 通过概率模型学习最优搜索区域
- 减少盲目搜索

❌ **局限**:
- EDA可能收敛到局部最优
- 嵌套结构导致计算开销大

---

## Algorithm 3: Two-Stage EDA-CostA* ⭐

### 核心思想
将EDA优化与高级启发式分离为两个阶段，通过聚类和自适应启发式提升搜索效率。

### 实现位置
[`core/path_planning/two_stage_eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\two_stage_eda_costastar.py) - `TwoStageEDACostAStarSearcher`类

### 算法架构

```
┌─────────────────────────────────────────┐
│  Stage 1: EDA Optimization              │
│  - 优化搜索空间                          │
│  - 输出最优种群 P_best                  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Stage 2: Post-processing & Enhancement │
│  - 提取开放点                            │
│  - K-means聚类                           │
│  - 计算高级启发式 (Eq. 24-25)           │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│  Stage 3: Enhanced CostA* Search        │
│  - 自适应启发式切换 (Eq. 26)            │
│  - 全局/局部引导平衡                     │
└─────────────────────────────────────────┘
```

### 详细流程

#### Stage 1: EDA迭代优化
```python
# 执行EDA迭代（30-50代）
best_path_from_eda = self.eda_searcher.search(start, goal)

# 提取最优搜索区域
best_region = self._extract_best_region(best_path_from_eda)
```

**关键点**:
- EDA优化的是**可行搜索区域掩码**（Feasible Region Mask）
- 适应度函数：路径总成本（无路则为inf）
- 概率矩阵更新公式（公式23）:
  ```
  p_{i+1} = (1 - α) * p_i + α * (1/N_s) * Σ Ds
  ```

#### Stage 2: 后处理与增强

##### 2.1 提取开放点
```python
open_points = self._extract_open_points(best_region)
```
从EDA输出的最优区域中提取所有可行单元格坐标。

##### 2.2 K-means聚类
```python
clusterer = KMeansClusterer(n_clusters=5)
centroids = clusterer.cluster(open_points)
```

**作用**: 
- 识别精英区域的"引力中心"
- 为局部启发式提供参考点

##### 2.3 计算高级启发式

**全局启发式 h_Dist** (公式24):
```python
h_Dist = h_heuDist * euclidean_distance(current, goal)
h_heuDist = min(mean_open_cost, mean_centroid_cost)
```

**局部启发式 h_Drctn** (公式25):
```python
h_Drctn = distance(current, nearest_centroid)
```

#### Stage 3: 增强CostA*搜索

**自适应启发式切换** (公式26):
```python
deviation = (h_Drctn - h_Dist_cen) / h_Dist_cen

if deviation < epsilon:
    h(c) = h_Drctn  # 局部引导（精细搜索）
else:
    h(c) = h_Dist   # 全局引导（快速收敛）
```

**参数 ε**: 通常设为0.1-0.3，控制切换敏感度。

### 创新点

1. **串行增强架构**: EDA与启发式解耦，避免嵌套导致的计算爆炸
2. **聚类引导**: K-means提取精英区域结构，提供局部引力点
3. **自适应切换**: 根据搜索状态动态平衡探索与利用

---

## 核心公式实现

### 公式1-10: Fatality Risk Model
**文件**: [`core/risk_model/fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py)

```python
# 公式4: 动能致死率
c_r_p = P_crash * P_fatal_pedestrian

# 公式5: 车辆撞击风险
c_r_v = P_crash * P_fatal_vehicle

# 公式9: 总致死风险
c_r_f = c_r_p + c_r_v
```

### 公式13-14: Property Damage Risk
**文件**: [`core/risk_model/property_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\property_risk.py)

```python
# 公式14: 建筑高度对数正态分布
psi_h = lognormal_pdf(h, mu, sigma)

# 公式13: 财产风险
c_r_pd = psi_h
```

### 公式15-17: Noise Impact
**文件**: [`core/risk_model/noise_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\noise_risk.py)

```python
# 公式15-17: 噪声传播模型
c_noise = varpi * L_h / (h^2 + d^2)
```

### 公式18-19: Integrated Cost Model
**文件**: [`core/risk_model/cost_model.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py)

```python
# 公式19: 归一化因子
omega_tau = 1 / c_tau_max

# 公式18: 集成成本
c_v = sum(alpha_tau * omega_tau * c_tau for tau in risks)
```

### 公式21: 26-Neighborhood Movement
**文件**: [`core/path_planning/graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py)

```python
# 3D空间中每个单元格有26个邻居
neighbors = [
    (dx, dy, dz) for dx in [-1, 0, 1]
                   for dy in [-1, 0, 1]
                   for dz in [-1, 0, 1]
                   if not (dx == 0 and dy == 0 and dz == 0)
]
```

### 公式22: Obstacle Avoidance
```python
if cell is building:
    cost = inf  # 禁止穿越建筑物
```

### 公式23: EDA Probability Update
**文件**: [`core/path_planning/eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py)

```python
# 概率矩阵更新
P_new = (1 - alpha) * P_old + alpha * mean(elite_population)
```

### 公式24-25: Advanced Heuristics
**文件**: [`core/path_planning/heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py)

```python
# 公式24: 全局启发式
h_Dist = h_heuDist * euclidean_dist(current, goal)

# 公式25: 局部启发式
h_Drctn = distance(current, nearest_centroid)
```

### 公式26: Adaptive Switching
**文件**: [`core/path_planning/enhanced_astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\enhanced_astar.py)

```python
deviation = (h_Drctn - h_Dist_cen) / h_Dist_cen

if deviation < epsilon:
    h(c) = h_Drctn  # 局部引导
else:
    h(c) = h_Dist   # 全局引导
```

---

## 性能对比

### 实验设置
- **测试环境**: 新加坡市中心模拟区域
- **网格尺寸**: 72 x 73 cells, 4层高度
- **单元格大小**: 80m
- **起止点**: (0,0,0) → (71,72,3)

### 结果对比

| 指标 | Standard A* | Original EDA | Two-Stage EDA |
|------|-------------|--------------|---------------|
| **总成本** | 98.17 | 99.00 | **98.17** |
| **总距离** | 8124m | 8320m | **8124m** |
| **航点数** | 73 | 75 | **73** |
| **运行时间** | ~2s | ~15s | ~20s |
| **迭代次数** | - | - | 57,505 |

### 结论

✅ **Two-Stage EDA-CostA***:
- 保持与Standard A*相同的最优解精度
- 相比Original EDA，成本降低0.83%
- 通过预筛选显著缩小搜索焦点
- 适合复杂城市环境的精细化路径规划

---

## 📚 相关文档

- **[FORMULAS.md](FORMULAS.md)** - 公式与代码对照表
- **[API_REFERENCE.md](API_REFERENCE.md)** - API参考手册
- **[VALIDATION_REPORT.md](VALIDATION_REPORT.md)** - 验证报告

---

**最后更新**: 2026-04-27
