# Manuscript2 实验实现计划

本文档给出一套面向论文写作的实验代码规划。目标是让 `06_case_study.tex` 不只是展示一条路径，而是能证明“时空异质风险建模”和“动态风险感知规划”确实带来差异。

## 1. 实验总原则

每个实验都应能回答一个清晰问题：

- 动态天气会不会改变航路？
- 人口潮汐会不会改变白天/夜间路径？
- 建筑峡谷和高度层会不会改变飞行高度选择？
- 风险权重变化会不会产生可解释的 Pareto trade-off？
- 分层/EDA 方法相对普通 A* 是否更快或更稳？

不要只报告“路径更安全”。要把安全拆成：

- final survival probability
- expected fatality
- expected property damage
- noise exposure
- flight distance
- runtime

## 2. 推荐实验目录

建议后续新增：

```text
methods/spatiotemporal_heterogeneity/experiments/
  run_synthetic_closed_loop.py
  run_micro_mechanism_cases.py
  run_weight_sensitivity.py
  run_algorithm_comparison.py
  export_paper_figures.py
  results/
    synthetic_closed_loop/
    micro_mechanisms/
    weight_sensitivity/
    algorithm_comparison/
```

每个实验目录保存：

```text
config.yaml
metrics.csv
path.json
tensor_summary.json
figures/
```

## 3. 实验 0：Synthetic Closed Loop

目的：确认项目流水线从合成数据到路径规划可以完整跑通。

流程：

```text
synthetic_data_factory
  -> DataPipeline(data_type="synthetic").run_all()
  -> build risk components
  -> EnvTensor
  -> AStar4D
  -> metrics + figures
```

输出：

- 一张 2D 风险底图叠加路径。
- 一张 3D 路径图。
- 一张沿路径的 `P_surv` 曲线。
- 一个 metrics 表。

验收指标：

- 路径成功。
- 所有张量 shape 与 grid 一致。
- `P_surv` 单调不增。
- `cum_fatality/property/noise` 单调不减。

## 4. 实验 1：天气风险机制

目的：支撑 `04_dynamic_tpr_models.tex` 中 `f_wind` 和 `f_rain` 的动态风险建模。

场景设计：

- 固定 OD。
- 中间设置一条强风/强雨带。
- 对比三种条件：
  - calm
  - strong wind
  - heavy rain

对比算法：

- distance-only A*
- dynamic-risk A*

预期现象：

- calm 下走近似直线。
- strong wind/heavy rain 下绕开高风险带。
- 若强风覆盖全域，可能因 `survival_threshold` 无解。

推荐图表：

- `p_crash(x,y,z_fixed,t_fixed)` 热力图。
- 三种路径叠加图。
- 表格：距离、存活概率、累计风险。

## 5. 实验 2：人口潮汐与噪声机制

目的：支撑人口/POI 潮汐模型和噪声社会影响模型。

场景设计：

- 同一 OD。
- 比较白天出发和夜间出发。
- 住宅区、商业区、学校/医院区放在不同区域。

对比：

- `t_start = 8:00`
- `t_start = 22:00`

预期现象：

- 白天可能避开学校/商业高敏区域。
- 夜间更强烈避开住宅区。
- 如果只用 distance-only A*，两条路径几乎相同；dynamic-risk A* 会随时间改变。

推荐图表：

- `R_noise(x,y,z_fixed,t_day)` 和 `R_noise(x,y,z_fixed,t_night)` 对比。
- 白天/夜间路径叠加。
- 沿路径噪声累积曲线。

## 6. 实验 3：建筑峡谷与高度层

目的：证明 4D 张量中的高度维 `z` 有意义。

场景设计：

- 中央高建筑群。
- 低空穿越有障碍或高 `f_obs`。
- 中高空绕过或跨越风险较低，但距离/爬升代价更高。

对比：

- 固定高度 A*。
- 允许高度变化的 3D/4D A*。

预期现象：

- 允许高度变化时，路径会选择升高或绕开。
- 高度层路径在风险和距离之间形成 trade-off。

推荐图表：

- 建筑高度图。
- 路径高度随步数变化曲线。
- `f_obs` 在不同 `z` 层的切片。

## 7. 实验 4：权重敏感性

目的：支撑多目标优化部分。

权重设置可以使用 `configs/cost_weight.yaml` 的三类模式：

- balanced
- emergency
- quiet_night
- strict_safety

建议额外扫一组权重：

```text
w_distance: 0.0 -> 0.8
w_fatality: 0.1 -> 0.8
w_noise: 0.0 -> 0.8
```

输出：

- 每组权重的路径和 metrics。
- trade-off 散点图：
  - distance vs fatality
  - distance vs noise
  - survival vs distance

注意：

如果当前 A* 未做单步归一化，不建议直接比较不同量纲权重。先实现归一化，再做敏感性实验。

## 8. 实验 5：算法对比

目的：支撑 `05_hierarchical_planning_algorithm.tex`。

基线算法：

1. Distance-only A*
2. Static-risk A*
3. Dynamic-risk A*
4. Proposed EDA-CostA* 或 hierarchical planner

指标：

| 指标 | 解释 |
|---|---|
| success rate | 多 OD / 多 seed 下是否找到路径 |
| objective cost | 归一化综合目标 |
| path length | 飞行距离 |
| final survival | 最终存活概率 |
| cum fatality | 累计期望致命风险 |
| cum property | 累计财产损失 |
| cum noise | 累计噪声影响 |
| runtime | 计算时间 |
| nodes explored | 搜索规模 |

对于 EDA-CostA*，还应记录：

- population size
- generations
- elite ratio
- corridor count
- local A* calls

## 9. 图表清单

建议最终论文至少准备这些图：

1. 系统流水线图：数据到张量到规划。
2. 4D 网格与 26 邻域图：已有初稿。
3. `f_wind`、`f_rain` 曲线：已有脚本。
4. 不同高度层 `f_obs` 切片。
5. 白天/夜间噪声热力图。
6. 天气场变化下路径对比。
7. 权重敏感性散点图。
8. 算法对比表。

## 10. 结果文件建议格式

`metrics.csv`：

```text
experiment_id,seed,algorithm,start,goal,t_start,
w_distance,w_fatality,w_property,w_noise,
status,path_length,total_time,final_survival,
cum_fatality,cum_property,cum_noise,objective_cost,
runtime,nodes_explored
```

`path.json`：

```json
{
  "grid_shape": [60, 60, 12, 96],
  "start": [2, 2, 5, 0],
  "goal": [57, 57, 5],
  "waypoints": [
    {
      "coords": [2, 2, 5, 0],
      "state": {
        "p_survival": 1.0,
        "cum_distance": 0.0
      }
    }
  ]
}
```

`tensor_summary.json`：

```json
{
  "p_crash": {"shape": [60, 60, 12, 96], "min": 0.0, "max": 0.001, "mean": 0.0001},
  "fatality": {"shape": [60, 60, 12, 96], "min": 0.0, "max": 1.2, "mean": 0.03},
  "property": {"shape": [60, 60, 12, 96], "min": 0.0, "max": 900.0, "mean": 20.0},
  "noise": {"shape": [60, 60, 12, 96], "min": 0.0, "max": 5.0, "mean": 0.2}
}
```

## 11. 论文写作反哺代码

当实验跑通后，建议反向补充 LaTeX：

- `05_hierarchical_planning_algorithm.tex`：根据真实实现写伪代码，而不是先写抽象愿景。
- `06_case_study.tex`：优先写 synthetic micro mechanism，再写 real/macro case。
- `appendix.tex`：详细记录 POI 潮汐生成器、参数表、seed 和 OD 设置。

论文和代码要保持同一组符号：

| 论文符号 | 代码变量 |
|---|---|
| `P_crash` | `p_crash` |
| `P_surv` | `p_survival` |
| `E_fatality` | `e_fatality` 或 `fatality` |
| `E_property` | `e_property` 或 `property` |
| `R_noise` | `noise` |
| `Delta t_fly` | `dt` |
| `J(pi)` | `objective_cost` |

## 12. 最短行动清单

1. 固定一个 `run_synthetic_closed_loop.py`。
2. 实现论文版风险累积和单步归一化。
3. 跑天气、噪声、建筑三组机制实验。
4. 生成 `metrics.csv` 和 3-4 张初稿图。
5. 再开始 EDA/hierarchical planner。
