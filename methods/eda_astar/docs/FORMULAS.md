# 公式实现对照表

**版本**: 1.0  
**最后更新**: 2026-04-27  
**参考论文**: Pang et al. (2022)

---

## 📋 目录

1. [风险模型公式](#风险模型公式)
2. [集成成本模型](#集成成本模型)
3. [路径规划算法公式](#路径规划算法公式)
4. [启发式函数公式](#启发式函数公式)
5. [代码映射索引](#代码映射索引)

---

## 风险模型公式

### 公式1-3: Crash Probability
**文件**: [`core/risk_model/fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py) Line 45-89

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.1** | $P_{crash} = f(m, v)$ | `p_crash = calculate_crash_probability(mass, velocity)` |
| **Eq.2** | $v = \sqrt{2gh}$ | `velocity = np.sqrt(2 * g * height)` |
| **Eq.3** | $E_k = \frac{1}{2}mv^2$ | `kinetic_energy = 0.5 * mass * velocity**2` |

---

### 公式4-9: Fatality Risk
**文件**: [`core/risk_model/fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py) Line 91-250

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.4** | $c_{r,p} = P_{crash} \times P_{fatal\_ped}$ | `c_r_p = p_crash * p_fatal_pedestrian` |
| **Eq.5** | $c_{r,v} = P_{crash} \times P_{fatal\_veh}$ | `c_r_v = p_crash * p_fatal_vehicle` |
| **Eq.6** | $P_{fatal\_ped} = f(E_k, \rho_{pop})$ | `p_fatal_ped = calculate_pedestrian_fatality(kinetic_energy, pop_density)` |
| **Eq.7** | $P_{fatal\_veh} = f(E_k, \rho_{traffic})$ | `p_fatal_veh = calculate_vehicle_fatality(kinetic_energy, traffic_density)` |
| **Eq.8** | $\rho_{pop} = \text{population density}$ | `pop_density = population_raster / cell_area` |
| **Eq.9** | $c_{r,f} = c_{r,p} + c_{r,v}$ | `c_r_f = c_r_p + c_r_v` |

**关键实现细节**:
```python
# Line 185-220: Pedestrian fatality probability
def calculate_pedestrian_fatality(kinetic_energy, pop_density):
    # Logistic regression model
    logit = beta0 + beta1 * np.log(kinetic_energy) + beta2 * pop_density
    p_fatal = 1 / (1 + np.exp(-logit))
    return p_fatal
```

---

### 公式10: Traffic Risk
**文件**: [`core/risk_model/traffic_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\traffic_risk.py) Line 50-180

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.10** | $c_{r,t} = f(\rho_{road}, \rho_{pop})$ | `c_r_t = road_density * population_density * weight` |

**实现逻辑**:
```python
# Line 120-150
def compute_traffic_risk(road_density, population_density):
    # Combined risk from road network and population
    risk = road_density * population_density * TRAFFIC_WEIGHT
    return normalize(risk)
```

---

### 公式13-14: Property Damage Risk
**文件**: [`core/risk_model/property_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\property_risk.py) Line 85-280

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.13** | $c_{r,pd} = \psi_h$ | `c_r_pd = psi_h` |
| **Eq.14** | $\psi_h = \frac{1}{h\sigma\sqrt{2\pi}} e^{-\frac{(\ln h - \mu)^2}{2\sigma^2}}$ | `psi_h = lognormal_pdf(h, mu, sigma)` |

**关键实现**:
```python
# Line 150-179: Log-normal distribution for building height
def lognormal_pdf(h, mu, sigma):
    if h <= 0:
        return 0
    return (1 / (h * sigma * np.sqrt(2 * np.pi))) * \
           np.exp(-(np.log(h) - mu)**2 / (2 * sigma**2))
```

**参数设置**:
- μ (mu): 建筑高度对数均值，通常 3.5-4.5
- σ (sigma): 建筑高度对数标准差，通常 0.5-1.0

---

### 公式15-17: Noise Impact
**文件**: [`core/risk_model/noise_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\noise_risk.py) Line 120-250

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.15** | $L_h = L_0 - 20\log_{10}(h/h_0)$ | `L_h = L_0 - 20 * np.log10(h / h_0)` |
| **Eq.16** | $d = \sqrt{(x-x_0)^2 + (y-y_0)^2}$ | `distance = np.sqrt((x - x0)**2 + (y - y0)**2)` |
| **Eq.17** | $c_{noise} = \varpi \frac{L_h}{h^2 + d^2}$ | `c_noise = varpi * L_h / (h**2 + d**2)` |

**实现细节**:
```python
# Line 185-220
def compute_noise_impact(height, horizontal_distance, L_0=80, varpi=0.5):
    # Sound pressure level at height h
    L_h = L_0 - 20 * np.log10(height / REF_HEIGHT)
    
    # Noise impact with distance decay
    noise_impact = varpi * L_h / (height**2 + horizontal_distance**2)
    
    return max(0, noise_impact)  # Ensure non-negative
```

---

## 集成成本模型

### 公式18-19: Integrated Cost
**文件**: [`core/risk_model/cost_model.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py) Line 150-280

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.18** | $c_v = \sum_{\tau} \alpha_\tau \cdot \omega_\tau \cdot c_\tau$ | `c_v = sum(alpha[tau] * omega[tau] * c_tau for tau in risks)` |
| **Eq.19** | $\omega_\tau = \frac{1}{c_{\tau,max}}$ | `omega_tau = 1.0 / c_tau_max` |

**完整实现**:
```python
# Line 156-224: Integrated cost computation
def compute_integrated_cost(risk_components, weights):
    """
    Args:
        risk_components: dict with keys ['fatality', 'property', 'noise', 'traffic']
        weights: dict with normalization weights
    
    Returns:
        Integrated cost value
    """
    # Normalize each risk component
    normalized = {}
    for risk_type, value in risk_components.items():
        omega = weights.get(risk_type, 1.0)
        normalized[risk_type] = value * omega
    
    # Weighted sum (Eq. 18)
    integrated_cost = sum(normalized.values())
    
    return integrated_cost
```

**权重配置** ([`config.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\config.py)):
```python
FATALITY_WEIGHT = 1.0
PROPERTY_WEIGHT = 0.8
NOISE_WEIGHT = 0.6
DISTANCE_WEIGHT = 1.0
```

---

## 路径规划算法公式

### 公式20: A* Evaluation Function
**文件**: [`core/path_planning/astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\astar.py) Line 80-150

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.20** | $f(n) = g(n) + h(n)$ | `f_score = g_score[current] + heuristic(current, goal)` |

**标准A*流程**:
```python
# Line 95-140
while open_set:
    current = min(open_set, key=lambda x: f_score[x])
    
    if current == goal:
        return reconstruct_path(came_from, current)
    
    for neighbor in get_neighbors(current):
        tentative_g = g_score[current] + cost(current, neighbor)
        
        if tentative_g < g_score[neighbor]:
            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            f_score[neighbor] = tentative_g + heuristic(neighbor, goal)
```

---

### 公式21: 26-Neighborhood Movement
**文件**: [`core/path_planning/graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py) Line 45-120

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.21** | $\mathcal{N}_{26} = \{(dx,dy,dz) \| dx,dy,dz \in \{-1,0,1\}\} \setminus \{(0,0,0)\}$ | See code below |

**实现**:
```python
# Line 50-80: Generate 26 neighbors
def get_26_neighbors(layer, row, col):
    neighbors = []
    for dz in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dz == 0 and dy == 0 and dx == 0:
                    continue  # Skip self
                
                new_layer = layer + dz
                new_row = row + dy
                new_col = col + dx
                
                if is_valid(new_layer, new_row, new_col):
                    neighbors.append((new_layer, new_row, new_col))
    
    return neighbors
```

**邻域类型**:
- **6-face neighbors**: (±1,0,0), (0,±1,0), (0,0,±1) - 距离 λ
- **12-edge neighbors**: (±1,±1,0), (±1,0,±1), (0,±1,±1) - 距离 λ√2
- **8-corner neighbors**: (±1,±1,±1) - 距离 λ√3

---

### 公式22: Obstacle Avoidance
**文件**: [`core/path_planning/graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py) Line 125-180

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.22** | $\text{cost}(c) = \begin{cases} \infty & \text{if } c \in \text{obstacle} \\ c_v & \text{otherwise} \end{cases}$ | `if is_obstacle(cell): return float('inf')` |

**实现**:
```python
# Line 130-160
def get_cell_cost(layer, row, col, cost_map, clearance=5.0):
    # Check if cell is within building footprint
    if is_inside_building(row, col, buildings):
        return float('inf')
    
    # Check clearance constraint
    if distance_to_nearest_building(row, col) < clearance:
        return float('inf')
    
    # Return integrated risk cost
    return cost_map[layer, row, col]
```

---

### 公式23: EDA Probability Update
**文件**: [`core/path_planning/eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py) Line 150-220

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.23** | $p_{i+1} = (1 - \alpha) \cdot p_i + \alpha \cdot \frac{1}{N_s} \sum D_s$ | `P_new = (1 - alpha) * P_old + alpha * np.mean(elite_population, axis=0)` |

**完整EDA更新流程**:
```python
# Line 160-210
def update_probability_matrix(P_old, elite_population, alpha=0.2):
    """
    Update probability matrix based on elite population
    
    Args:
        P_old: Current probability matrix (3D array)
        elite_population: List of binary masks (elite individuals)
        alpha: Learning rate
    
    Returns:
        Updated probability matrix
    """
    # Calculate mean of elite population
    elite_mean = np.mean(elite_population, axis=0)
    
    # Update rule (Eq. 23)
    P_new = (1 - alpha) * P_old + alpha * elite_mean
    
    # Clamp to [0, 1]
    P_new = np.clip(P_new, 0.0, 1.0)
    
    return P_new
```

---

## 启发式函数公式

### 公式24: Global Heuristic h_Dist
**文件**: [`core/path_planning/heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py) Line 88-135

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.24** | $h_{Dist}(c) = h_{heuDist} \times d_{euclid}(c, goal)$ | `h_Dist = h_heuDist * euclidean_distance(current, goal)` |

**其中**:
$$h_{heuDist} = \min(\bar{c}_{open}, \bar{c}_{centroid})$$

**实现**:
```python
# Line 95-130
def compute_global_heuristic(current, goal, open_costs, centroid_costs):
    """
    Compute global heuristic function (Eq. 24)
    
    Args:
        current: Current node coordinates
        goal: Goal node coordinates
        open_costs: Costs of open points from EDA
        centroid_costs: Costs of cluster centroids
    
    Returns:
        h_Dist value
    """
    # Euclidean distance to goal
    euclid_dist = np.linalg.norm(np.array(current) - np.array(goal))
    
    # Heuristic scaling factor
    h_heuDist = min(np.mean(open_costs), np.mean(centroid_costs))
    
    # Final heuristic
    h_Dist = h_heuDist * euclid_dist
    
    return h_Dist
```

---

### 公式25: Local Heuristic h_Drctn
**文件**: [`core/path_planning/heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py) Line 137-156

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.25** | $h_{Drctn}(c) = d(c, c_{nearest})$ | `h_Drctn = distance(current, nearest_centroid)` |

**实现**:
```python
# Line 140-156
def compute_local_heuristic(current, centroids):
    """
    Compute local heuristic function (Eq. 25)
    
    Args:
        current: Current node coordinates
        centroids: List of cluster centroid coordinates
    
    Returns:
        h_Drctn value (distance to nearest centroid)
    """
    # Find nearest centroid
    distances = [np.linalg.norm(np.array(current) - np.array(c)) 
                 for c in centroids]
    
    h_Drctn = min(distances)
    
    return h_Drctn
```

---

### 公式26: Adaptive Switching
**文件**: [`core/path_planning/enhanced_astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\enhanced_astar.py) Line 90-121

| 公式 | 数学表达 | 代码实现 |
|------|---------|---------|
| **Eq.26** | $h(c) = \begin{cases} h_{Drctn}(c) & \text{if } \delta < \epsilon \\ h_{Dist}(c) & \text{otherwise} \end{cases}$ | See code below |

**其中偏差计算**:
$$\delta = \frac{h_{Drctn} - h_{Dist}^{cen}}{h_{Dist}^{cen}}$$

**完整实现**:
```python
# Line 95-121
def adaptive_heuristic(current, goal, centroids, open_costs, epsilon=0.2):
    """
    Adaptive heuristic switching (Eq. 26)
    
    Args:
        current: Current node
        goal: Goal node
        centroids: Cluster centroids
        open_costs: Open point costs
        epsilon: Switching threshold
    
    Returns:
        Selected heuristic value
    """
    # Compute both heuristics
    h_Dist = compute_global_heuristic(current, goal, open_costs, centroids)
    h_Drctn = compute_local_heuristic(current, centroids)
    
    # Reference value (centroid-based distance)
    h_Dist_cen = compute_centroid_distance(current, centroids)
    
    # Calculate deviation
    deviation = (h_Drctn - h_Dist_cen) / h_Dist_cen
    
    # Adaptive switching
    if deviation < epsilon:
        # Local guidance (fine-grained search)
        return h_Drctn
    else:
        # Global guidance (fast convergence)
        return h_Dist
```

**参数 ε 的影响**:
- **ε = 0.1**: 更频繁使用局部引导，搜索更精细但可能较慢
- **ε = 0.2**: 平衡选择（推荐）
- **ε = 0.3**: 更倾向全局引导，收敛更快但可能错过局部最优

---

## 代码映射索引

### 快速查找表

| 公式编号 | 核心文件 | 关键函数/类 | 行号范围 |
|---------|---------|------------|---------|
| Eq.1-3 | [`fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py) | `calculate_crash_probability` | 45-89 |
| Eq.4-9 | [`fatality_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\fatality_risk.py) | `compute_fatality_risk` | 91-250 |
| Eq.10 | [`traffic_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\traffic_risk.py) | `compute_traffic_risk` | 50-180 |
| Eq.13-14 | [`property_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\property_risk.py) | `lognormal_pdf` | 85-280 |
| Eq.15-17 | [`noise_risk.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\noise_risk.py) | `compute_noise_impact` | 120-250 |
| Eq.18-19 | [`cost_model.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\risk_model\cost_model.py) | `compute_integrated_cost` | 150-280 |
| Eq.20 | [`astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\astar.py) | `CostAStarSearcher.search` | 80-150 |
| Eq.21 | [`graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py) | `get_26_neighbors` | 45-120 |
| Eq.22 | [`graph.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\graph.py) | `get_cell_cost` | 125-180 |
| Eq.23 | [`eda_costastar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\eda_costastar.py) | `update_probability_matrix` | 150-220 |
| Eq.24 | [`heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py) | `compute_global_heuristic` | 88-135 |
| Eq.25 | [`heuristic_calculator.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\heuristic_calculator.py) | `compute_local_heuristic` | 137-156 |
| Eq.26 | [`enhanced_astar.py`](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\core\path_planning\enhanced_astar.py) | `adaptive_heuristic` | 90-121 |

---

## 📚 相关文档

- **[ALGORITHMS.md](ALGORITHMS.md)** - 算法完整说明
- **[API_REFERENCE.md](API_REFERENCE.md)** - API参考手册
- **[VALIDATION_REPORT.md](VALIDATION_REPORT.md)** - 验证报告

---

**最后更新**: 2026-04-27
