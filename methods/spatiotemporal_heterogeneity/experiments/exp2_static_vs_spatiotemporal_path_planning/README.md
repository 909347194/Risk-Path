# Exp 2 — Static Risk vs Spatiotemporal Risk（核心实验）

> 实验类型：**论文核心对比**（直接回答"为什么不用时间平均的静态风险图？"）
> 入口：`python3 run.py`（12 次 A* 搜索 + 统一后评估，约 3 min）
> 产物：`results/fig1_paths.png`、`fig2_method_bars.png`、`fig3_adaptation.png`、
> `comparison.csv`、`summary.csv`、`regret.csv`
> （`results/` 按仓库约定不入库）

## 1. 目的 (Purpose)

如果论文的核心贡献是 *spatiotemporal heterogeneity-aware UAV path planning*，
审稿人第一反应必然是：

> **"Why can't I just use an average/static risk map?"**

本实验正面回答：三种规划目标在同一 OD、同一权重口径下对比，
证明时间平均风险图会在特定出发时刻付出**显著的安全代价**，
而时空感知规划随出发时刻自适应调整路径。

## 2. 三种方法 (Methods)

固定同一 OD、同一权重，仅「风险项的时间口径」不同：

| 方法 | 目标函数 | 说明 |
|---|---|---|
| **Baseline 1** Distance-only A* | $J = \sum_k d_k$ | 只考虑距离（风险权重全 0） |
| **Baseline 2** Static-Risk A* | $J = \sum_k \bar C(x_k,y_k,z_k) + w_d d_k$，$\bar C = \frac{1}{T}\sum_t C(x,y,z,t)$ | 一天风险的时间平均图 |
| **Proposed** Spatiotemporal A* | $J = \sum_k C(x_k,y_k,z_k,t_k) + w_d d_k$ | 风险逐时相在线采样（本文方法） |

**统一后评估（公平性关键）**：无论用什么目标规划出的路径，都放回
**真实时空风险场**上按 `astar_4d._expand_node` 的同一口径重算全部指标
（hazard 累加 $H=-\sum\ln(1-p)$、$P_{surv}=e^{-H}$、后果项、飞行时间）。
→ 三种方法的 Distance / Risk / Survival / Time 四列完全可比。

## 3. 数据与方法 (Data & Method)

- **真实数据**（`data/02_processed` 只读加载，与 Exp1 完全同源），
  宏观网格 100×100×12，96 时相 × 15 min；
- 风险张量由 `build_risk_tensors` 组装（情景风 + 情景雨 + 人口潮汐 + 建筑峡谷）；
- **OD = (5,70) → (95,5)**（与 Exp1 当前配置一致的双核走廊），**60 m 定高巡航**；
- 出发时刻 **08:00 / 12:00 / 18:00 / 22:00**，3 方法 × 4 时刻 = 12 次搜索；
- 权重与 Exp1 主设定一致（w_risk/w_ops = 1000）。

> 定高锁的必要性：自由高度（`cruise_altitude_lock: false`）在本网格上会打满
> A* 的 `max_iterations=1e6`（标签空间 100×100×12×8），Exp1 实测 4 个时刻全部
> `open_set_exhausted`（该 reason 也覆盖迭代上限）。定高锁既保证搜索可控
> （单次 ~7 s），也排除高度自由度对三种方法的不对称影响。

## 4. 结果 (Results, 2026-09-29)

> 数值来源：`results/comparison.csv`、`summary.csv`、`regret.csv`（真实时空场统一后评估）。

**逐出发时刻**（Distance / Risk(H) / Survival / Time=飞行时间）：

| 时刻 | 方法 | Distance (m) | Risk (H) | Survival | Time (s) |
|---|---|---|---|---|---|
| 08:00 | Distance-only | 5642.0 | 3.091 | 0.0454 | 564 |
|       | Static-Risk    | 7278.3 | 3.073 | 0.0463 | 728 |
|       | **Spatiotemporal** | **7221.9** | **3.058** | **0.0470** | 722 |
| 12:00 | Distance-only | 5642.0 | 2.692 | 0.0677 | 564 |
|       | Static-Risk    | 7278.3 | 2.627 | 0.0723 | 728 |
|       | **Spatiotemporal** | **7098.8** | **2.465** | **0.0850** | 710 |
| 18:00 | Distance-only | 5642.0 | 2.366 | 0.0938 | 564 |
|       | Static-Risk    | 7278.3 | 2.263 | 0.1041 | 728 |
|       | **Spatiotemporal** | **7098.8** | **2.119** | **0.1202** | 710 |
| 22:00 | Distance-only | 5642.0 | 2.530 | 0.0797 | 564 |
|       | Static-Risk    | 7278.3 | 2.447 | 0.0865 | 728 |
|       | **Spatiotemporal** | **7098.8** | **2.294** | **0.1009** | 710 |

**跨时刻均值**：

| Method | Distance (m) | Risk (H) | Survival | Time (s) |
|---|---|---|---|---|
| Distance-only A* | 5642.0 | 2.670 | 0.0717 | 564 |
| Static-Risk A* | 7278.3 | 2.602 | 0.0773 | 728 |
| **Spatiotemporal A* (ours)** | **7129.5** | **2.484** | **0.0883** | 713 |

**关键观察**：

1. **静态方法无法适应时间**：Static-Risk 四个时刻路径完全相同（7278.3 m，
   Figure 1 四面板同一条线）；时空感知路径随时段调整（08:00 与其他时段不同路）；
2. **逐时刻全面占优**：时空方法的累计风险 H 在**每个出发时刻都低于**静态方法
   （3.058<3.073 / 2.465<2.627 / 2.119<2.263 / 2.294<2.447），12:00 改善最大（−6.2%）；
3. **安全代价真实存在**：最差安全后悔值 = Distance-only @ 18:00，存活率差距 0.0264
   （0.0938 → 0.1202，相对 +28.1%），H 超出 0.248；
4. **均值收益**：存活率 0.0883 vs 静态 0.0773（+14.2%）、vs 距离最优 0.0717（+23.1%）；
5. 静态方法相对距离最优的改进有限（H 2.602 vs 2.670，−2.5%），因为平均图
   不知道 08:00 是全天最危险时段——**这正是「静态图答不好」的直接证据**。

**结论：时间平均风险图不能替代时空风险建模；出发时刻改变时，静态方法既不换路
也无法规避时段性风险峰值，而时空感知规划逐时刻取得更低风险与更高存活率。**

## 5. 图表说明 (Figures)

- **Figure 1** `fig1_paths.png`：2×2 四个出发时刻面板，真实 P_crash 切片为底，
  叠加三种方法的路径。看点：static/distance 四面板同一条线（无法适应时间），
  时空感知路径随时刻移动。
- **Figure 2** `fig2_method_bars.png`：逐时刻分组柱状图（距离 / 累计风险 / 存活率）。
- **Figure 3** `fig3_adaptation.png`：适应性曲线——存活率与累计风险随出发时刻变化；
  static/distance 的曲线随城市风险节律起伏（危险时段安全裕度被吃掉），
  时空感知曲线更优更稳。`regret.csv` 给出逐时刻「安全后悔值」。

## 6. 备注 (Notes)

- 与 Exp1 的关系：Exp1 证明"风险场时空异质性存在"（机制）；本实验进一步证明
  "这种异质性**值得利用**"（方法收益），是论文证据链的第 2 环；
- 与 Exp3（消融）的分工：本实验只对比三种**目标口径**，不做组件消融；
- `P_surv` 绝对值口径问题同 Exp1（15min/格暴露放大），不影响方法间相对比较
  （同一后评估口径）。
