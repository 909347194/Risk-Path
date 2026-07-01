# Manuscript2 代码实现路线图

本文代码目标不是单纯跑出一条 A* 路径，而是支撑论文中“风险时空异质性如何改变城市低空无人机航路规划”的完整证据链。建议按从闭环到论文实验的顺序实现，避免一开始就追求真实 GIS、EDA、K-means 和可视化全部完备。

## 1. 论文主线

`paper/manuscript2` 当前的核心技术内容集中在三处：

- `03_system_architecture.tex`：定义 4D 时空网格、状态向量、风险累积、约束和目标函数。
- `04_dynamic_tpr_models.tex`：定义动态第三方风险模型，包括坠机概率、致命风险、财产损失和噪声影响。
- `05_hierarchical_planning_algorithm.tex`：计划写分层混合规划算法，目前还是占位，需要代码实验反过来补充文字。

代码实现应围绕一个统一数据流：

```text
synthetic/real raw data
  -> data_provision: landuse, building, road, pop, POI, weather
  -> tensor_engine: p_crash, E_fatality, E_property, R_noise, obstacle
  -> algorithms: A* / EDA-CostA*
  -> experiments: ablation, sensitivity, comparison
  -> visualization: paper figures and tables
```

`methods/spatiotemporal_heterogeneity` 已经基本按照这个分层搭好。后续不要让 `algorithms` 直接读取原始 GIS，也不要让 `data_provision` 生成风险张量。

## 2. 最小可发表闭环

先完成一个可重复的 synthetic 闭环，再扩展真实数据。最小闭环建议如下：

1. `utils/synthetic_data_factory` 生成合成城市底图。
2. `src/data_provision.pipeline.DataPipeline(data_type="synthetic").run_all()` 产出：
   - `landuse_map`
   - `building_heights`
   - `road_mask`
   - `rho_population`
   - `rho_vehicle`
   - `wind_field`
   - `rain_data`
3. `src/tensor_engine` 将上述数据组装成：
   - `p_crash(x,y,z,t)`
   - `E_fatality(x,y,z,t)`
   - `E_property(x,y,z)`
   - `R_noise(x,y,z,t)`
   - `obstacle(x,y,z,t)` 或 `obstacle(x,y,z)`
4. `src/algorithms.EnvTensor` 接收风险分量。
5. `src/algorithms.a_star.AStar4D` 输出路径和累计指标。
6. `src/visualization` 绘制路径、风险切片、累计风险曲线。

这个闭环应该成为所有后续论文实验的基准入口。

## 3. 当前代码与论文模型的关键差距

当前代码已经有可运行结构，但仍需对齐论文公式。

### 3.1 风险累积公式

论文 `03_system_architecture.tex` 中致命风险和财产风险写的是：

```text
C_fatality += P_surv * P_crash * E_fatality
C_property += P_surv * P_crash * E_property
C_noise += P_surv * R_noise * dt
```

当前算法层实现更接近：

```text
C_fatality += P_surv * fatality * dt
C_property += P_surv * property * dt
C_noise += noise * dt
```

后续要二选一并统一：

- 方案 A：`tensor_engine` 输出的 `fatality/property` 已经包含 `P_crash` 和时间步长，则算法层不再重复乘。
- 方案 B：`tensor_engine` 输出的是后果强度 `E_fatality/E_property`，算法层按论文公式乘 `P_crash`。

推荐采用方案 B，因为论文公式更清楚，也方便做消融实验。

### 3.2 单步归一化目标函数

论文中提出了基于张量极值的单步无量纲化：

```text
Delta J = w1 * Delta C_fatal_norm
        + w2 * Delta C_property_norm
        + w3 * Delta C_noise_norm
        + w4 * Delta C_dist_norm
```

当前 `AStar4D` 使用累计原始值加权。建议新增一个 `CostNormalizer` 或在 `EnvTensor` 中预计算：

- `Omega_fatality = max(P_crash * E_fatality)`
- `Omega_property = max(P_crash * E_property)`
- `Omega_noise = max(R_noise) * dt_step_max`
- `L_step_max = sqrt(dx^2 + dy^2 + dz^2)`

然后 A* 的 `g` 使用归一化单步增量累计。这样更贴合论文，也能解释为什么不同量纲的风险可以合并。

### 3.3 电池约束表达

论文约束写的是路径长度 `L_max`，当前代码更多用 `max_battery_time`。建议同时支持：

- `max_battery_time`
- `max_path_length`

实验中可将二者互相换算：`L_max = v_uav * max_battery_time`。

## 4. 推荐开发顺序

### 阶段 1：张量出口固定

目标：让 `tensor_engine` 有一个稳定的、可测试的函数返回算法所需全部分量。

建议新增实验脚本，而不是大改现有模块：

```text
methods/spatiotemporal_heterogeneity/experiments/build_risk_components.py
```

输出结构：

```python
{
    "grid": grid,
    "p_crash": p_crash_4d,
    "fatality": e_fatality_4d,
    "property": e_property_3d_or_4d,
    "noise": noise_4d,
    "obstacle": obstacle_3d_or_4d,
}
```

验收标准：

- 所有张量形状可被 `EnvTensor(grid=grid)` 接收。
- 无 NaN/Inf。
- `p_crash` 在 `[0, 1]`。
- obstacle 是布尔或 0/1。

### 阶段 2：标准 A* 对齐论文公式

目标：让 `AStar4D` 成为论文第三章和第四章的直接实现。

建议实现选项：

```python
config = {
    "risk_mode": "consequence",  # fatality/property are E_* not already multiplied by p_crash
    "normalize_step_cost": True,
    "w_fatality": 0.3,
    "w_property": 0.15,
    "w_noise": 0.15,
    "w_distance": 0.4,
}
```

验收标准：

- 能复现 `P_surv` 连乘下降。
- 能记录每一步 `delta_fatality/delta_property/delta_noise/delta_distance`。
- 输出既有原始累计值，也有归一化目标值。

### 阶段 3：微观机制实验

目标：用小网格证明模型机制，不急着追求真实城市复杂度。

建议实验：

- 风速增强：同一 OD，在强风区出现绕行。
- 夜间住宅噪声：白天和夜间路径不同。
- 高建筑峡谷：同一 OD，在低空绕避或提高高度。
- 安全阈值：提高 `P_th` 后路径更保守或无解。

这些图最适合支撑 `03` 和 `04` 章节。

### 阶段 4：分层算法

等标准 A* 闭环稳定后，再实现 `05_hierarchical_planning_algorithm.tex`：

- K-means 或风险低谷聚类提取候选走廊。
- EDA 在走廊级别采样全局结构。
- CostA* 在局部网格中精修。

不要一开始就实现 EDA。否则很容易算法复杂，但基础风险张量和论文指标还没有对齐。

### 阶段 5：城市级案例

目标：服务 `06_case_study.tex`。

应包含：

- 数据源说明：synthetic 或 real GIS。
- OD 对选择：至少 3 组，短程/中程/穿越高风险区。
- 对比算法：
  - distance-only A*
  - static-risk A*
  - dynamic-risk A*
  - proposed hierarchical / EDA-CostA*
- 指标表：
  - path length
  - flight time
  - final survival probability
  - expected fatality
  - property cost
  - noise cost
  - computation time

## 5. 实现纪律

- 所有随机过程必须有 `seed`。
- 所有实验输出写入 `output/` 或 `experiments/results/`，不要混入源码目录。
- 每个实验保存配置快照，尤其是权重、阈值、OD、seed。
- 每个核心张量都保存 shape/range/mean 统计，方便论文写实验设置。
- 论文公式和代码变量名尽量一致：`p_crash`, `e_fatality`, `e_property`, `r_noise`, `p_survival`。

## 6. 下一步最值得做的三件事

1. 写一个 `experiments/run_synthetic_closed_loop.py`，串起 pipeline、tensor_engine、EnvTensor、AStar4D。
2. 修改或扩展 A* 的代价更新，使其支持论文公式中的 `P_crash * E_*` 和单步归一化。
3. 为 `03` 和 `04` 章节生成 3-4 张机制图，而不是先追求最终城市大图。
