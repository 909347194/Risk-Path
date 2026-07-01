# Manuscript2 公式到代码模块映射

本文档用于把 `paper/manuscript2` 的数学模型映射到 `methods/spatiotemporal_heterogeneity` 的代码实现。后续写代码时优先检查这里，避免公式、变量名和模块职责逐渐漂移。

## 1. 总体章节映射

| 论文位置 | 论文内容 | 建议代码位置 | 当前状态 |
|---|---|---|---|
| `03_system_architecture.tex` | 4D 时空网格 | `src/tensor_engine/grid_system.py` | 已有 |
| `03_system_architecture.tex` | 状态向量 `S_i` | `src/algorithms/common.py` | 已有基础 |
| `03_system_architecture.tex` | 状态演化与风险累积 | `src/algorithms/a_star/astar_4d.py` | 需继续对齐公式 |
| `04_dynamic_tpr_models.tex` | `f_wind`, `f_rain`, `f_obs`, `P_crash` | `src/tensor_engine/dynamic_p_crash.py`, `static_obstacle.py` | 已有基础 |
| `04_dynamic_tpr_models.tex` | 动态人口/车辆暴露 | `src/data_provision/spatiotemporal_tidal_model.py` | 已有基础 |
| `04_dynamic_tpr_models.tex` | 致命风险 | 建议补齐到 `src/tensor_engine/dynamic_population.py` 或新模块 `dynamic_fatality.py` | 部分已有 |
| `04_dynamic_tpr_models.tex` | 财产损失风险 | `src/tensor_engine/static_obstacle.py::PropertyDamageModel` | 部分已有 |
| `04_dynamic_tpr_models.tex` | 噪声社会影响 | `src/tensor_engine/dynamic_noise.py` | 已有 |
| `05_hierarchical_planning_algorithm.tex` | K-means 走廊 + EDA-CostA* | `src/algorithms/eda_a_star/` | 待实现 |
| `06_case_study.tex` | 实验与对比 | `experiments/` | 待补齐 |

## 2. 数据维度约定

论文中的连续空间和时间：

```text
V subset R^3, T = [0, Tmax]
```

代码中统一离散为：

```text
grid.shape = (nx, ny, nz, nt)
```

分层职责：

| 数据 | 推荐形状 | 负责模块 |
|---|---:|---|
| `landuse_map` | `(nx, ny)` | `data_provision` |
| `building_heights` | `(nx, ny)` | `data_provision` |
| `road_mask` | `(nx, ny)` | `data_provision` |
| `rho_pop` | `(nx, ny, nt)` | `data_provision` |
| `rho_vehicle` | `(nx, ny, nt)` | `data_provision` |
| `wind_field` | `(nx, ny, nt)` 或 `(nx, ny, nz, nt)` | `data_provision/tensor_engine` |
| `rain_data` | `(nx, ny, nt)` | `data_provision` |
| `p_crash` | `(nx, ny, nz, nt)` | `tensor_engine` |
| `e_fatality` | `(nx, ny, nz, nt)` | `tensor_engine` |
| `e_property` | `(nx, ny, nz)` 或 `(nx, ny, nz, nt)` | `tensor_engine` |
| `r_noise` | `(nx, ny, nz, nt)` | `tensor_engine` |
| `obstacle` | `(nx, ny, nz)` 或 `(nx, ny, nz, nt)` | `tensor_engine` |

`algorithms` 只消费这些张量，不负责生成它们。

## 3. 4D 环境风险元组

论文定义：

```text
R_env(x, y, z, t) = <P_crash, R_fatality, R_property, R_noise>
```

代码建议对应：

```python
EnvTensor(
    p_crash=p_crash,
    fatality=e_fatality,
    property=e_property,
    noise=r_noise,
    obstacle=obstacle,
    grid=grid,
)
```

注意命名：论文中 `R_fatality` 有时可能表示“最终风险”，有时又像“坠机后果强度”。为避免歧义，代码里建议明确区分：

- `e_fatality`: 坠机发生后的期望伤亡后果。
- `fatality_cost`: 已乘上 `P_crash` 和 `P_surv` 后的路径累计项。
- `p_crash`: 当前时空点坠机概率。

## 4. 坠机概率模型

论文：

```text
f_wind = exp(k_w * (v_wind / V_limit)^theta), if v < V_limit
f_rain = 1 + gamma * I_rain^2
f_obs = 1 + K_obs * R_canyon
P_crash = 1 - exp(-lambda_base * Phi * dt)
Phi = f_wind * f_rain * f_obs
```

代码位置：

- `src/tensor_engine/dynamic_p_crash.py`
- `src/tensor_engine/static_obstacle.py`

建议实现方式：

```python
f_wind = crash_model.compute_wind_factor(wind_4d)
f_rain = crash_model.compute_rain_factor(rain_4d)
f_obs = obstacle_model.compute_f_obs(...)  # broadcast to 4D
p_crash = crash_model.compute_pcrash(f_wind, f_rain, f_obs, dt=step_dt)
```

关键检查：

- 风速超过阈值时 `p_crash` 应接近 1 或直接被标记为不可飞。
- `f_rain` 不应出现负值。
- `f_obs` 应在开阔区域接近 1，在峡谷区域明显增大。

## 5. 致命风险模型

论文写法：

```text
c_rf = c_rp + c_rv
c_rp = P_crash * N_hit^p * R_f^p
N_hit^p = S_hit * rho_pop(x,y,t)
c_rv = P_crash * N_hit^v * R_f^v
N_hit^v = S_hit * rho_veh(x,y,t)
```

建议代码拆分：

```text
tensor_engine:
  e_fatality = N_hit_p * R_f_p + N_hit_v * R_f_v

algorithms:
  delta_fatality = P_surv * P_crash * e_fatality
```

也就是说，`tensor_engine` 输出“坠机后果强度”，`algorithms` 再乘“路径到达概率”和“局部坠机概率”。这样和论文状态演化一致。

建议新增或整理：

```text
src/tensor_engine/dynamic_fatality.py
```

核心函数：

```python
compute_impact_velocity(height, mass, drag_coeff, hit_area, air_density)
compute_fatality_rate(impact_energy, alpha, beta, shelter_coeff)
compute_fatality_consequence(rho_pop, rho_vehicle, grid, params)
```

## 6. 财产损失模型

论文：

```text
r_b^k(h)
r_b(h) = sum_k r_b^k(h) * S_b^k * I{h <= h_b^k}
```

当前 `PropertyDamageModel` 已提供简化版本。建议后续明确输出语义：

```text
e_property(x,y,z) = crash consequence property loss
```

算法层累计：

```text
delta_property = P_surv * P_crash * e_property
```

如果暂时无法实现完整建筑价值分布，可保留简化模型，但论文中要说明是 proxy / surrogate。

## 7. 噪声模型

论文：

```text
Cost_noise(i, z, t)
  = I_noise(z) * rho_pop(i,t) * S_landuse(i) * T_penalty(t)
I_noise(z) = L_ref / (z^2 + d^2)
```

代码位置：

- `src/tensor_engine/dynamic_noise.py`

建议：

- `tensor_engine` 输出 `r_noise(x,y,z,t)`，表示单位时间噪声影响率。
- `algorithms` 累计：

```text
delta_noise = P_surv * r_noise * dt_fly
```

当前如果算法没有乘 `P_surv`，要么改代码，要么在论文中删掉“受存活概率限制”的表述。推荐改代码，保留论文逻辑。

## 8. 状态向量与 A*

论文状态：

```text
S_i = [p_i, t_i, Psi_i]^T
Psi_i = [P_surv, C_fatality, C_property, C_noise]
```

代码对应：

```python
SearchNode.coords = (x, y, z, t)
SearchNode.state = {
    "absolute_time": ...,
    "cum_distance": ...,
    "cum_time": ...,
    "p_survival": ...,
    "cum_fatality": ...,
    "cum_property": ...,
    "cum_noise": ...,
}
```

建议补充字段：

```python
"cum_objective": ...
"last_delta": {
    "fatality": ...,
    "property": ...,
    "noise": ...,
    "distance": ...
}
```

这样后续能直接画路径上的风险累积曲线。

## 9. 约束条件

论文约束：

```text
p_0 = p_start
p_N = p_goal
p_{i+1} in N26(p_i)
p_i not in U_cba
P_surv >= P_th
sum distance <= L_max
```

代码对应：

- 起终点：`AStar4D.search(start, goal)`
- 26 邻域：`_get_neighbors`
- 障碍：`EnvTensor.obstacle`
- 存活阈值：`survival_threshold`
- 电池/距离：建议同时支持 `max_battery_time` 和 `max_path_length`

注意：论文有 loop-free 约束。A* 的 closed set 可以避免无意义回环，但在 4D 时间状态下，同一空间点不同时间可能重复出现。实验中若要严格 loop-free，应额外记录路径空间节点集合，或在论文中说明使用最优搜索的 dominated-state 剪枝替代显式 loop-free。

## 10. 建议的统一结果结构

每次规划应返回：

```python
{
    "status": "success",
    "path": [
        {
            "coords": (x, y, z, t),
            "state": {...},
            "risk": {
                "p_crash": ...,
                "e_fatality": ...,
                "e_property": ...,
                "r_noise": ...,
            },
            "delta": {
                "fatality": ...,
                "property": ...,
                "noise": ...,
                "distance": ...,
                "objective": ...,
            }
        }
    ],
    "total_distance": ...,
    "total_time": ...,
    "final_p_survival": ...,
    "cum_fatality": ...,
    "cum_property": ...,
    "cum_noise": ...,
    "objective_cost": ...,
    "nodes_explored": ...,
    "time_cost": ...
}
```

这个结构能直接服务论文中的表格、路径图和风险曲线。
