# Manuscript2 算法设计指导建议

本文档基于 `paper/manuscript2/03_system_architecture.tex` 与 `paper/manuscript2/04_dynamic_tpr_models.tex`，专门给出算法设计层面的落地建议。重点不是再罗列公式，而是说明这些公式应如何变成一个自洽、可验证、能支撑论文实验的路径规划算法。

## 1. 算法定位

这篇论文的核心算法不宜被表述为普通 A* 的简单加权改造，而应定位为：

> 面向动态第三方风险张量的时间扩展约束最短路算法。

也就是说，算法的输入不是二维代价地图，而是随空间、高度和时间变化的风险场；算法的状态也不只是当前位置，而至少包含：

```text
S_i = (x_i, y_i, z_i, t_i, H_i, C_fatality_i, C_property_i, C_noise_i, L_i)
```

其中 `H_i = -ln(P_surv_i)` 是累计失效风险强度。推荐在代码里保存 `H_i`，而不是只保存 `P_surv_i`，因为：

- `P_surv` 是连乘量，长路径上容易数值下溢。
- `H` 是加法量，更适合搜索、剪枝和约束判断。
- 生存约束可写为 `H_i <= -ln(P_th)`，比反复比较连乘概率更稳定。

最终输出时再由 `P_surv_i = exp(-H_i)` 还原即可。

## 2. 首先固定风险张量语义

第 3 章和第 4 章之间最容易产生歧义的是风险变量的含义。建议在算法实现中采用以下数据契约。

| 张量 | 推荐含义 | 推荐形状 | 是否由算法再乘 `P_crash` |
|---|---|---:|---|
| `hazard_rate` | 局部坠机危险率，即 `lambda_base * Phi(x,y,z,t)` | `(nx, ny, nz, nt)` | 否 |
| `p_crash_step` | 当前边上的局部坠机概率，由 `hazard_rate` 和 `dt_fly` 动态计算 | 标量 | 已是局部概率 |
| `e_fatality` | 若在该点坠机，造成的期望死亡人数后果 | `(nx, ny, nz, nt)` | 是 |
| `e_property` | 若在该点坠机，造成的财产损失后果 | `(nx, ny, nz)` 或 `(nx, ny, nz, nt)` | 是 |
| `r_noise` | 单位时间噪声社会影响率 | `(nx, ny, nz, nt)` | 否 |
| `obstacle` | 建筑、禁飞、极端风等硬约束 | `(nx, ny, nz)` 或 `(nx, ny, nz, nt)` | 否 |

强烈建议算法内部优先使用 `hazard_rate`，而不是预先固定死的 `P_crash(x,y,z,t)`。原因是 26 邻域中的直线、平面对角线和三维对角线边长不同，飞行时间 `dt_fly` 也不同。局部坠机概率应在扩展边时计算：

```text
p_crash_step = 1 - exp(-hazard_rate(x_next,y_next,z_next,t_next) * dt_fly)
```

这样才能严格对应第 3 章的时间推演方程，避免把固定时间片概率错误地用于不同长度的边。

## 3. 推荐的单步转移计算

从节点 `u` 扩展到邻居 `v` 时，算法应按以下顺序计算。

```text
distance = ||p_v - p_u||
dt_fly = distance / v_uav
t_v = t_u + dt_fly
t_idx = time_index_policy(t_v)
```

然后查询风险张量并计算：

```text
h_step = hazard_rate(v, t_idx) * dt_fly
p_crash_step = 1 - exp(-h_step)
p_surv_u = exp(-H_u)

delta_fatality = p_surv_u * p_crash_step * e_fatality(v, t_idx)
delta_property = p_surv_u * p_crash_step * e_property(v)
delta_noise = p_surv_u * r_noise(v, t_idx) * dt_fly
delta_distance = distance

H_v = H_u + h_step
```

这个顺序与论文逻辑一致：致死风险和财产风险只有在“无人机存活到达当前段”且“当前段发生坠机”时兑现；噪声风险不需要坠机，但需要无人机存活并持续飞行。

## 4. 时间离散策略必须明确

第 3 章定义了 `t_k = k * Delta t`，但算法中的 `t_i = distance / v_uav` 通常不是整数时间片。因此代码和论文都应明确一种时间索引策略。

推荐策略：

```text
t_idx = floor(t / Delta t) 或线性插值
```

如果追求实现简单，先用 `floor` 或 `nearest`；如果论文要强调动态时变风险的精度，建议使用时间线性插值：

```text
risk(t) = (1-alpha) * risk[k] + alpha * risk[k+1]
alpha = (t - k*Delta t) / Delta t
```

需要注意：如果采用 `ceil`，算法会偏保守；如果采用 `floor`，算法可能低估即将到来的风险变化。建议在实验设置中说明采用哪一种，并在敏感性分析中检查 `Delta t` 对路径结果的影响。

## 5. 目标函数建议

第 3 章提出了基于时空张量极值的单步无量纲化策略。算法应同时维护“原始风险指标”和“归一化搜索代价”。

推荐单步目标函数：

```text
Delta J =
  w_fatality * delta_fatality / Omega_fatality
+ w_property * delta_property / Omega_property
+ w_noise * delta_noise / Omega_noise
+ w_distance * distance / L_step_max
```

其中：

```text
Omega_fatality = max(hazard_rate_edge_to_pcrash * e_fatality)
Omega_property = max(hazard_rate_edge_to_pcrash * e_property)
Omega_noise = max(r_noise) * dt_step_max
L_step_max = sqrt(3) * d_res
```

实现时要给分母加极小值保护：

```text
denominator = max(Omega, eps)
```

否则在某些合成场景中，如果某类风险全为零，会出现除零错误。

## 6. 搜索算法选择

### 6.1 第一阶段：Dynamic Risk Cost-A*

第一阶段建议实现一个严格对齐论文公式的 `DynamicRiskAStar`，作为所有实验的主基线。它应具备：

- 4D 时间扩展状态。
- 26 邻域空间扩展。
- 边耗时 `dt_fly` 动态计算。
- 累计危险率 `H`。
- 生存阈值、障碍、电池或航程硬约束。
- 原始累计风险与归一化目标值同步输出。

若要宣称“最优”，启发式函数必须是可证明的下界。最稳妥的启发式是只使用距离下界：

```text
h(n) = w_distance * euclidean_distance(n, goal) / L_step_max
```

风险项可以先不进入启发式，因为动态风险的未来下界难以严格证明。若使用带风险估计的启发式，应在论文中表述为加速搜索的经验型 Weighted A*，不要称为严格最优。

### 6.2 第二阶段：标签支配的多标签搜索

当前模型有一个重要特征：同一 `(x,y,z,t)` 节点可能由不同路径到达，具有不同的 `H`、累计距离和累计风险。简单的 closed set 只按坐标关闭节点，可能错误剪掉后续更优路径。

更严谨的做法是为每个时空网格保存多个非支配标签。标签 `A` 支配标签 `B` 的充分条件可定义为：

```text
J_A <= J_B
H_A <= H_B
L_A <= L_B
C_fatality_A <= C_fatality_B
C_property_A <= C_property_B
C_noise_A <= C_noise_B
```

且至少一项严格小于。被支配的标签可以安全丢弃。

如果实现多标签搜索成本过高，可以在第一版中使用标量 `J` 的 A*，但论文应谨慎表述为“基于综合代价的近似最优搜索”。后续若想增强学术严谨性，多标签剪枝是最值得补的一步。

### 6.3 第三阶段：分层规划

当 `DynamicRiskAStar` 闭环稳定后，再设计分层算法。推荐结构：

```text
全局层：在粗分辨率网格或风险聚类图上寻找低风险走廊
局部层：在走廊附近用 DynamicRiskAStar 精修 4D 路径
重规划层：当天气或人流张量更新时，从当前位置重新规划
```

分层算法的论文贡献可以表述为提高城市级大网格上的计算效率，而不是替代风险模型本身。风险模型的可信度仍然由第 4 章和 DynamicRiskAStar 基线承担。

## 7. 约束设计建议

第 3 章已有障碍、生存概率和电池约束。算法实现时建议细化为以下硬约束。

| 约束 | 实现建议 |
|---|---|
| 建筑障碍 | `obstacle[x,y,z] == True` 直接不可扩展 |
| 极端风 | `v_wind >= V_limit` 直接标记为不可飞，而不是仅设置极大代价 |
| 生存概率 | 使用 `H <= -ln(P_th)` 判断 |
| 航程/电池 | 同时支持 `max_path_length` 和 `max_flight_time` |
| 高度范围 | 限制 `z_min <= z <= z_max` |
| 爬升/下降 | 对邻接边增加 `abs(dz)/dt_fly <= v_z_max` |
| 转弯约束 | 若论文要强调动力学，可把航向加入状态；否则不要过度声称“完整动力学约束” |

如果不加入航向状态，26 邻域只能表达基本连通性和爬升约束，不能严格表达最小转弯半径。

## 8. 噪声风险的算法化处理

第 4 章的噪声公式本质上是“无人机位置对地面受体单元的影响”。因此 `r_noise(x,y,z,t)` 不应只取无人机正下方一个网格的人口密度，而更合理的做法是对一定半径内地面受体聚合：

```text
r_noise(x,y,z,t) =
sum over ground cell i [
  P_ref / (z^2 + d_i^2)
  * rho_pop(i,t)
  * S_landuse(i)
  * T_penalty(t)
]
```

为了降低计算量，可以预计算不同高度层的距离衰减卷积核，对每个时间片的人口-敏感度图做卷积。这样算法查询时仍然只是一次张量读取，但物理含义比“只看脚下网格”更稳。

## 9. 财产风险的算法化处理

财产风险建议分两层处理：

```text
obstacle(x,y,z): 建筑实体占据，硬约束
e_property(x,y,z): 坠机后果或贴近建筑飞行的财产风险，软代价
```

二者不要混在一起。建筑实体内部应不可飞；建筑附近或低于高楼高度的区域可以通过 `e_property` 和 `f_obs` 提高软风险。这样算法既能保证不穿模，又能体现高建筑密集区对路径选择的影响。

## 10. 实验应服务算法设计

建议用以下实验证明算法设计是必要的。

| 实验 | 目的 | 预期现象 |
|---|---|---|
| 距离 A* vs DynamicRiskAStar | 证明风险张量会改变路径 | 风险算法绕开高人流、高建筑或强风区 |
| 静态风险 vs 动态风险 | 证明时间维有意义 | 白天/夜间或不同天气时间窗路径不同 |
| 有无生存阈值 | 证明硬安全约束有效 | 阈值升高后路径更保守，极端情况下无解 |
| 有无噪声项 | 证明社会影响成本有效 | 夜间住宅区绕行或升高 |
| 单标签 vs 多标签 | 证明标签支配的价值 | 多标签在复杂动态场景中获得更低综合代价 |
| 不同 `Delta t` | 检查时间离散稳健性 | 时间分辨率变细后路径和指标趋于稳定 |

论文中至少要保留前三类实验。否则第 3、4 章的复杂模型很容易被审稿人质疑为“堆公式但没有算法必要性”。

## 11. 最小可交付算法接口

建议最终规划器接口保持简洁：

```python
planner = DynamicRiskAStar(
    env=env_tensor,
    weights={
        "fatality": 0.35,
        "property": 0.15,
        "noise": 0.15,
        "distance": 0.35,
    },
    constraints={
        "survival_threshold": 0.99,
        "max_path_length": 8000.0,
        "z_min": 30.0,
        "z_max": 120.0,
        "vz_max": 4.0,
    },
    normalize_step_cost=True,
    time_sampling="linear",
)

result = planner.search(start, goal, departure_time=0.0)
```

返回结果至少包含：

```text
path
objective_cost
total_distance
total_time
final_survival_probability
cum_fatality
cum_property
cum_noise
nodes_expanded
runtime
per_step_records
```

`per_step_records` 非常重要，它决定后续能否直接画论文中的累计风险曲线、风险分量柱状图和路径时空剖面图。

## 12. 当前最建议优先完成的三件事

1. 将算法输入从 `p_crash` 优先改为 `hazard_rate`，在扩展边时根据 `dt_fly` 计算 `p_crash_step`。
2. 用 `H = -ln(P_surv)` 作为搜索状态的一部分，并用 `H <= -ln(P_th)` 实现生存约束。
3. 实现并记录严格的单步风险增量：`delta_fatality`、`delta_property`、`delta_noise`、`delta_distance`、`delta_objective`。

这三点完成后，代码就能与第 3、4 章形成比较紧密的闭环；再往后才值得投入分层走廊、EDA 或更复杂的启发式搜索。

