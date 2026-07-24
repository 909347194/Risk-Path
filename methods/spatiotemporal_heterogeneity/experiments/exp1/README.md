# EXP1: 微观机制验证实验 (Micro-Scale Mechanism Validation)

## 1. 实验目标

在 400m × 400m 的合成城市场景中，验证 TD-RiskA\* 算法的四个核心学术观点：

1. **时间节律自适应性** — 同一 OD 对在不同出发时刻生成不同路径
2. **微气象-地形耦合避让** — 风/雨热点与建筑峡谷耦合时路径主动绕行
3. **噪声-安全帕累托权衡** — 调整权重时噪声与安全呈现 Pareto 前沿
4. **时间自适应路径选择 + Label-Setting 理论分析** — 风暴窗口绕行 + k=1 即保证最优

## 2. 场景配置

### Exp1~3: 微观场景 (scenario_builder)

| 参数     | 值                 | 来源                    |
| -------- | ------------------ | ----------------------- |
| 空间范围 | 400m × 400m × 120m | `scenario_builder.py`   |
| 网格维度 | 40 × 40 × 12       | 10m 水平分辨率          |
| 时间维度 | 24 步 (1h/步)      | 24 小时模拟             |
| UAV 速度 | 10 m/s             | `common.yaml`           |
| 飞行高度 | z=5 (50m)          | 低空巡航                |
| OD 对    | (2,2) → (37,37)    | 西南→东北对角线         |

场景内建时间变化的风/雨热点（非外部叠加）：
- 风场：12-18时中心风速 +8m/s（接近 V_limit），其余时段 +1~4m/s
- 降雨：14-20时中心雨强 +15mm/h，其余时段无雨
- 人口潮汐：商业区 08-18时 ×5，住宅区 22-06时 ×4

### Exp4: 峡谷瓶颈场景 (独立构建)

| 参数     | 值                   |
| -------- | -------------------- |
| 网格维度 | 100 × 100 × 12 × 48 |
| 空间分辨率 | 50m                |
| 时间分辨率 | 30min              |
| 场景     | 中央建筑墙 + 窄缺口 + 时间变化风速 |

## 3. 文件结构

```
experiments/exp1/
├── README.md                              # 本文档
├── EXPERIMENT_ANALYSIS.md                 # 详细实验分析报告
├── scenario_builder.py                    # 共享场景构建工具 (Exp1~3)
├── run_exp1_temporal_adaptability.py      # 实验1: 时间节律
├── run_exp2_microclimate_terrain.py       # 实验2: 微气象-地形
├── run_exp3_noise_safety_pareto.py        # 实验3: 帕累托权衡
├── run_exp4_pruning_efficiency.py         # 实验4: 时间自适应 + 剪枝分析
├── run_micro_comprehensive.py             # 综合实验 (基线/敏感性/统计/Scaling)
└── run_random_od_pareto.py                # 随机 OD Pareto 鲁棒性

experiments/output/EXP1-output/
├── exp1_temporal/                         # 实验1 输出
├── exp2_microclimate/                     # 实验2 输出
├── exp3_pareto/                           # 实验3 输出
├── exp4_pruning/                          # 实验4 输出
└── micro_comprehensive/                   # 综合实验输出
```

## 4. 运行方式

```bash
# 在项目根目录运行
cd Risk-Path

# 实验1: 时间节律自适应性
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_exp1_temporal_adaptability

# 实验2: 微气象-地形耦合
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_exp2_microclimate_terrain

# 实验3: 噪声-安全帕累托权衡
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_exp3_noise_safety_pareto

# 实验4: 时间自适应 + 剪枝分析
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_exp4_pruning_efficiency

# 综合实验
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_micro_comprehensive

# 随机 OD Pareto 鲁棒性
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1.run_random_od_pareto
```

## 5. 实验结果

### 实验 1: 时间节律自适应性

| 出发时刻           | 路径长度 | 存活概率  | 累积噪声   | 搜索节点 | 运行时间  |
| ------------------ | -------- | --------- | ---------- | -------- | --------- |
| 08:00 (早高峰)     | 495m     | 0.187     | 0.0025     | 179      | 4.4ms     |
| 12:00 (午间)       | 495m     | 0.058     | 0.0021     | 179      | 4.2ms     |
| **18:00 (晚高峰)** | **513m** | **0.011** | 0.0016     | **4864** | **344ms** |
| 22:00 (夜间)       | 495m     | 0.259     | **0.0040** | 179      | 4.3ms     |

- 18:00 晚高峰路径绕行 +18m（+3.5%），搜索节点暴增 27×（风+雨叠加导致中心区 P_crash 极高）
- 22:00 夜间存活率最高（无风雨），噪声最高（T_penalty ×10）

### 实验 2: 微气象-地形耦合避让

| 条件     | 算法          | 路径长度 | 存活概率  | 累积致死    | 累积财产   |
| -------- | ------------- | -------- | --------- | ----------- | ---------- |
| Calm     | Distance-only | 495m     | 0.058     | 0.00109     | 0.0        |
| Calm     | TD-RiskA\*    | 495m     | 0.058     | 0.00109     | 0.0        |
| **Wind** | Distance-only | **589m** | 0.021     | 0.00160     | **9.92**   |
| **Wind** | TD-RiskA\*    | **597m** | **0.016** | **0.00090** | **0.0**    |
| Rain     | Distance-only | 536m     | 0.014     | 0.00127     | 0.059      |
| Rain     | TD-RiskA\*    | 536m     | 0.010     | 0.00074     | 0.0        |

- **Wind**: TD-RiskA\* 绕行更远（+8m），致死降 44%（0.0009 vs 0.0016），财产损失降 100%（0 vs 9.92）
- **Rain**: 路径相同，但 TD-RiskA\* 存活率更低（0.010 vs 0.014）——因权重配置不同

### 实验 3: 噪声-安全帕累托权衡

OD 穿过住宅走廊，夜间出发（t=22）。

| w_noise | 路径长度 | 累积噪声 | 累积致死 | 存活概率 | 目标函数 J |
| ------- | -------- | -------- | -------- | -------- | ---------- |
| 0.01    | 530m     | 5.68     | 0.082    | 0.147    | 21.60      |
| 0.05    | 530m     | 5.68     | 0.082    | 0.147    | 20.11      |
| 0.10    | 530m     | 5.68     | 0.082    | 0.147    | 18.63      |
| 0.20    | 530m     | 5.68     | 0.082    | 0.147    | 15.68      |
| 0.30    | 530m     | 5.68     | 0.082    | 0.147    | 12.72      |
| 0.50    | 530m     | 5.68     | 0.082    | 0.147    | 8.30       |
| 0.70    | 530m     | 5.68     | 0.082    | 0.147    | 3.88       |
| **0.85**| **671m** | **2.18** | **0.030**| 0.102    | **1.14**   |

- **Pareto 前沿**：w_n=0.70→0.85 时路径跳变（530m→671m），噪声降 62%，致死降 64%
- 跳变前：所有权重产生相同路径，仅 J 值变化
- 跳变后：绕行避开住宅走廊，噪声和致死同时降低

### 实验 4: 时间自适应 + Label-Setting 分析

**Part A — 时间扫描**（100×100 峡谷瓶颈场景）：

| 时段     | 对应时间     | 路径    | 存活率 | 搜索节点 | 运行时间  |
| -------- | ------------ | ------- | ------ | -------- | --------- |
| t=0~22   | 00:00-11:00  | 4450m   | 0.170  | 1223     | ~80ms     |
| **t=24~34** | **12:00-17:00** | **4997m** | **0.195** | **50932** | **~13s** |
| t=36~46  | 18:00-23:00  | 4450m   | 0.170  | 1223     | ~80ms     |

- 风暴窗口期间路径绕行 +12.3%，存活率反而更高（0.195 vs 0.170）

**Part B — k 值消融**：

| k 值 | t=0 (无风暴) | t=24 (风暴中) | t=36 (风暴后) |
| ---- | ------------ | ------------- | ------------- |
| 1    | 4450m, J=18.71 | 4997m, J=21.03 | 4450m, J=18.71 |
| 128  | 4450m, J=18.71 | 4997m, J=21.03 | 4450m, J=18.71 |

- **所有 k 值产生完全相同的最优路径** — 这是理论性质：J/H/t 单调递增 → k=1 即保证最优

## 6. 算法参数

### 权重预设

| 预设          | w_d  | w_f  | w_p  | w_n  | 场景     |
| ------------- | ---- | ---- | ---- | ---- | -------- |
| default       | 0.40 | 0.30 | 0.15 | 0.15 | 均衡模式 |
| emergency     | 0.80 | 0.10 | 0.05 | 0.05 | 医疗急救 |
| quiet_night   | 0.20 | 0.20 | 0.10 | 0.50 | 深夜静音 |
| strict_safety | 0.00 | 0.70 | 0.20 | 0.10 | 绝对安全 |

## 7. 依赖关系

```
scenario_builder.py
  ├── synthetic_data_factory  (合成数据生成)
  ├── tensor_engine           (风险张量构建)
  │   ├── dynamic_p_crash     (坠机概率)
  │   ├── dynamic_fatality    (致死后果)
  │   ├── static_obstacle     (财产损失)
  │   └── dynamic_noise       (噪声成本)
  └── algorithms
      ├── env_tensor          (环境张量容器)
      └── a_star/astar_4d     (TD-RiskA* 搜索)
```

## 8. 已知限制

1. **合成数据简化**：建筑、土地利用为规则分布，非真实城市形态
2. **Exp3 Pareto 跳变是离散的**：栅格路径规划的固有特性，无渐进过渡
3. **Exp4 Label-Setting 无额外收益**：论文需重新定位贡献（k=1 即最优）
4. **无 EDA 对比**：当前仅实现 A\*，未包含 EDA-K-means 层次化算法
