# Exp 2 — Static Risk vs Spatiotemporal Risk（核心实验）

> 实验类型：**论文核心对比**（直接回答"为什么不用时间平均的静态风险图？"）
> 入口：`python3 run.py`（12 次 A* 搜索 + 统一后评估，定高锁单次 ~7 s）
> 产物：`results/fig1_paths.png`（→论文 Figure 2）、`fig2_method_bars.png`、
> `fig3_adaptation.png`、`table1_main_results.csv`（→论文 Table 1，主结果）、
> `summary.csv`、`path_difference.csv`、`regret.csv`
> （`results/` 按仓库约定不入库）

## 1. 目的 (Purpose)

如果论文的核心贡献是 *spatiotemporal heterogeneity-aware UAV path planning*，
审稿人第一反应必然是：

> **"Why can't I just use an average/static risk map?"**

本实验正面回答：**三组公平对照**在同一 OD、同一权重口径下对比，证明时间平均
风险图会在特定出发时刻付出**显著的安全代价**，而时空感知规划随出发时刻自适应
调整路径。

**为什么一定要有 Distance-only（M1）**：否则 reviewer 会问"Static Risk 和
Spatiotemporal Risk 都绕风险区域，到底是不是风险建模在起作用？"——
Distance-only 提供完整 baseline chain（无风险项 → 静态风险项 → 时空风险项）。

## 2. 三组公平对照 (Methods)

固定同一 OD、同一 A*、同一权重，**仅「风险项的时间口径」不同**：

| 编号 | 方法 | 目标函数 | 说明 |
|---|---|---|---|
| **M1** | Distance-only A* | $J = L$ | 只考虑距离（风险权重全 0），最基础 baseline |
| **M2** | Static Risk A* | $J = L + \lambda\, \bar C(x,y,z)$，$\bar C = \frac{1}{T}\sum_t C(x,y,z,t)$ | 时间平均风险图（审稿人建议的替代方案） |
| **M3** | Spatiotemporal Risk A* | $J = L + \lambda\, C(x,y,z,t)$ | 风险逐时相在线采样（**本文方法**） |

**实现口径**：

- 目标函数的归一化实现与论文公式对应（`astar_4d._expand_node`，论文 §3.4 Eq.10）：
  $\delta J = w_f \delta C_f/\Omega_f + w_p \delta C_p/\Omega_p + w_n \delta C_n/\Omega_n + w_d\, d/d_{max}$；
  $\lambda \equiv w_{risk}/w_{ops} = 1000$（与 Exp1 主设定一致）。$J$ 乘任意正常数
  不改变 argmin，故 M2/M3 共用同一组权重，仅风险时间口径不同；M1 即 $w_d=1$、
  风险权重全 0。
- **M2 静态场按「成本级时间平均」构建**（`build_static_env`）：保证静态模型的
  单步期望后果成本恰为真实单步成本的时间平均（$\bar C = \frac{1}{T}\sum_t C$），
  不留 $E[p]\cdot E[f] \neq E[p\cdot f]$ 的口径偏差；
- 建筑硬约束是静态的，三种方法共用同一套 obstacle（否则可行性不对称）。

**统一后评估（公平性关键）**：无论用什么目标规划出的路径，都放回
**真实时空风险场**上按 `astar_4d._expand_node` 的同一口径重算全部指标
（hazard 累加 $H=-\sum\ln(1-p)$、$P_{surv}=e^{-H}$、后果项、飞行时间、计算时间）。
→ 三种方法的 Length / Risk / Survival / Runtime 列完全可比。

## 3. 数据与方法 (Data & Method)

- **真实数据**（`data/02_processed` 只读加载，与 Exp1 完全同源），
  宏观网格 100×100×12，96 时相 × 15 min；
- 风险张量由 `build_risk_tensors` 组装（情景风 + 人口潮汐 + 建筑峡谷；
  降雨与 Exp1 口径一致关闭，保证两实验建立在同一个风险场上）；
- **OD = (8,61) → (95,5)**（与 Exp1 当前配置一致的双核走廊），**60 m 定高巡航**；
  > 旧起点 (5,70) 处建筑高 57.6 m，在 60 m 层（障碍下界 50 m）被判为障碍
  > （建筑硬约束张量接入后 planner 报 `start_in_obstacle`），已与 Exp1 同步
  > 南移 9 格到 (8,61)（建筑 18.9 m，畅通）。
- 出发时刻 **08:00 / 12:00 / 18:00 / 22:00**，3 方法 × 4 时刻 = **12 次搜索**；
- 控制变量：同一 OD、同一出发时刻集、同一权重、同一后评估口径——
  唯一自变量是「风险项的时间口径」与「出发时刻」。

> 定高锁的必要性：本实验聚焦「时间」维度对比，定高锁排除高度自由度对三种方法
> 的不对称影响；且解锁定高单次搜索 ~2.5 min（Exp1 冒烟实测），定高单次 ~7 s，
> 12 次搜索可控。

**极端局地危险事件情景（演示「时间感知路由」价值，默认开启）**：诊断表明，真实
风险场的时间异质性在空间上近乎相干（早高峰全城统一缩放，`risk(08:00)/risk(18:00)`
空间 CV≈0.03），导致即便不加情景，ST 路径 ≈ Static 且跨时刻不变（见 §6）。为演示
本文方法在「时间维度可被利用」时的价值，引入一个**局部、时段性**的高风险脉冲
（高斯衰减，中心 `(10,24)`、半径 16、`08:00–13:00` 活跃、峰值 ×12），物理上对应
一片**局地极端天气/危险单体（强对流暴雨胞 / 临时限飞区）**在部分时段扫过航路。
机制：Static 用时间平均场 → 热点被 24 h 抹平为弱信号、仍直穿；ST 在活跃时刻看到
完整危险 → 绕开，冷时段走直线。
> **为何不直接用项目内置 `ScenarioRainEnvironment`**：该模型 `I(x,y,t)=I_ref·S(x,y)·T(t)`
> 本身即「空间局部(hotspot)+时段性」场，概念同源；但实测（见 §6）其在 realistic
> 强度下 `f_rain=1+γ·I²` 仅 ~1.3×、热点 `p_crash` 仅 0.03→0.036，无法驱动走廊切换；
> 即便 heavy(25 mm/h，已超平台运行上限 `R_limit=10`) 也只到 ~0.10，规划器仍直穿
> （path-change rate=0.00）。根因：基础风险场已高且空间异质，雨的物理增益（γ、运行
> 上限封顶）结构上到不了"近不可通行"（`p_crash→~0.95`）。故演示用脉冲参数化到可
> 演示量级。**这是实验演示情景（非真实数据），论文中须明确标注为
> extreme-localized-event scenario（非日常气象条件）**；真实数据基线（关闭
> `params.localized_hazard`）仍给出 §6 的边际结论。

## 4. 指标与判读原则 (Metrics & How to Read)

**指标（全部统一后评估）**：

| 指标 | 含义 | 列名 |
|---|---|---|
| $L$ | 路径长度 | `length_m` |
| $R_{fatal}$ | 致死风险（期望致死后果累计） | `fatal_risk` |
| $R_{property}$ | 财产风险 | `property_risk` |
| $R_{noise}$ | 噪声风险 | `noise_risk` |
| $P_{survival}$ | 生存概率 | `survival` |
| $T_{compute}$ | 计算时间（规划耗时） | `runtime_s` |
| $H$ | 累计危险率 $-\sum\ln(1-p)$（结论判定用复合风险量） | `hazard_H` |
| $D(P_{static}, P_{ST})$ | 两路径平均几何偏离（双向最近点均值） | `path_difference.csv` |
| path-change rate | 到对方路径最近点 > 1 格对角线的采样点占比（双向平均；0=同一走廊） | `path_difference.csv` |

> **为什么必须有 path difference / path-change rate**：本文关注的是
> 「时空风险是否真的改变了路径决策」——除了风险指标下降，还必须直接看到
> 路径决策改变的证据（$D(P_{static},P_{ST})$ 与 path-change rate）。
> `path_difference.csv` 还含 `hours_per_method` 行：同一方法跨出发时刻的路径
> 变化（Static 理论上恒为 0：无法适应时间；ST 应 > 0）。

> ### ⚠️ 判读原则（重要）
>
> 本实验最重要的结果**不是"距离变短"**。不要把 "Spatiotemporal path 比
> static path 短" 当成主要目标。真正应该看的是：
>
> $$\boxed{R_{ST} < R_{Static}}\quad \text{同时}\quad L_{ST} \approx L_{Static}$$
>
> 或者 $L_{ST} > L_{Static}$ 但风险显著下降——这才体现 risk-aware planning 的
> trade-off。`run.py` 的 [Conclusion] 段按此口径输出（逐时刻 ΔH/ΔL + 胜率），
> 禁止把「更短」写成卖点。

## 5. 输出 (Outputs)

**Table 1（`table1_main_results.csv`，主结果表）**——列顺序即论文表口径：

| Time | Method | Length | Fatal risk | Property | Noise | Survival | Runtime |
|---|---|---|---|---|---|---|---|

（CSV 附加诊断列：`hazard_H`、`travel_time_s`、`status`、`reason`；失败行指标留空。）

**Figure 2（`fig1_paths.png`）**：一个代表性 OD 叠加风险场，2×2 四个出发时刻
面板 × 三种方法路径（白描边保证热力图背景上可辨），每个面板标注
$D(P_{static},P_{ST})$ 与 path-change rate，ST 偏离 static 走廊的区段用高亮点
标出；共享色条 + 全局单图例——让 reviewer 一眼看到 *same OD + different
departure time + different risk model → different route decisions*。

**辅助图表**：`fig2_method_bars.png`（六指标分组柱状，柱顶标数值、含量纲注记），
`fig3_adaptation.png`（(a)(b) 存活率/危险率随出发时刻——x 轴按真实时间间距并
标注 4h/6h/4h；(c) L–H trade-off 散点，Static→ST 箭头即主结论图证），
`summary.csv`（跨时刻均值 + 相对 Static 的风险/长度对比列）、`regret.csv`
（逐时刻安全后悔值）。绘图样式统一由 `plot/style.py` 管理（配色/线型/标记，
线型双重编码保证黑白打印可辨）。

## 6. 结果 (Results)

**真实数据基线（关闭 `localized_hazard`）**：时间异质性空间相干 → ST 路径 ≈
Static（`D≈4 m`、`change-rate≈0.01`），跨时刻仍不变（ST 最大 change-rate=0）；
ST 相对 Static 风险仅低 ~1.3%。即真实相干场上时空建模收益有限——这是诚实的
基线结论。

**降雨情景实测（为何未采用为演示机制）**：为检验"直接用项目内置降雨模型
`ScenarioRainEnvironment` 能否替代上面的脉冲情景"，开启 `params.rain`
（`scenario=heavy`、`spatial_mode=hotspot`、中心 `(34,13)`、半径 16、活跃
`[8,13]`）重跑。实测结论：
- `f_rain=1+γ·I²`（γ=0.005）受平台运行降雨上限 `R_limit=10 mm/h` 封顶，realistic
  强度（中雨 8 mm/h）热点 `p_crash` 仅 0.033→0.036（+10%），全局几乎不动；
- 即便 heavy(25 mm/h，**已超运行上限、无人机应停飞**)，热点 `p_crash` 也只到
  ~0.097（×3），远未达"近不可通行"（需 `p_crash→~0.95` 才能逼出绕行）；
- 规划结果：Static 路径 4 时刻完全相同（L=6784.5 m），ST 与 Static 分歧仅
  1.7–4.2 m，**path-change rate=0.00**，ST 跨时刻最大 change-rate=0.00，ST 相对
  Static 仅 +0.57%——**雨未产生任何路径决策改变**。
- 根因：基础风险场已高且空间异质（背景 `p_crash` 0.03–0.15），雨的物理增益在 realistic
  强度下不足以制造"可过 vs 不可过"的区分，规划器评估后宁可直穿。该发现本身说明
  **内置降雨模型对"局部时间风险"的敏感度偏低**，是模型层面的结论（需在论文中明确）。
  因此演示机制仍采用上方脉冲情景（同等物理语义、参数化到可演示量级）。

**局部时间热点情景（开启 `localized_hazard`，演示「时间可被利用」时的价值）**：
热点活跃时段（08/12）ST 与 Static 路径分歧 `D=566–590 m`、`change-rate=0.74`
（走廊切换）；ST 跨出发时刻最大 `change-rate=0.74`（随时刻换走廊）。安全收益
决定性（统一后评估）：

| Time | Static $P_{surv}$ | ST $P_{surv}$ | $\Delta H$(static−ST) | $\Delta L$(ST vs static) |
|---|---|---|---|---|
| 08:00 | 0.0003 | 0.0646 | +5.30 | −19.1% |
| 12:00 | 0.0011 | 0.0968 | +4.46 | −18.4% |
| 18:00 | 0.1210 | 0.1348 | +0.11 | −3.4% |
| 22:00 | 0.1016 | 0.1142 | +0.12 | −3.4% |

- 活跃时段 Static 直穿时间平均后仍危险的热点区（$P_{surv}$ 千分之三），ST 绕开后
  存活率提升两个数量级——这是「为什么不用时间平均静态风险图」的直接图证
  （fig1 背景可见热点，ST 绕行）。
- 冷时段热点关闭，ST ≈ Static（分歧回落），符合预期。
- ST 在 4/4 时刻 $R_{ST} < R_{static}$；mean $\Delta L = -11.1\%$（活跃时段因绕开
  危险走廊反而更短，冷时段小幅溢价 3.4%——安全代价项，非卖点）。

结论判定（run.py [Conclusion] 自动输出）：
1. $R_{ST} < R_{Static}$ 在多少个出发时刻成立（本设定 4/4）；
2. $\Delta L(ST\ vs\ static)$（活跃时段可更短，冷时段小幅溢价）；
3. $D(P_{static},P_{ST})$ 与 path-change rate（路径决策改变的直接证据，活跃时段
   change-rate≈0.74 = 走廊切换）；
4. Static 跨时刻 path-change rate（≡ 0）vs ST（>0 = 时间自适应）。

## 7. 备注 (Notes)

- 与 Exp1 的关系：Exp1 证明"风险场时空异质性存在"（机制）；本实验进一步证明
  "这种异质性**值得利用**"（方法收益），是论文证据链的第 2 环；
- 与 Exp3（消融）的分工：本实验只对比三种**目标口径**，不做组件消融；
- `P_surv` 绝对值口径问题同 Exp1（15min/格暴露放大），不影响方法间相对比较
  （同一后评估口径）；
- 降雨可经 `config.yaml` 的 `params.rain.enabled: true` 一键开启（配套
  `scenario/spatial_mode/center/radius/active_hours` 覆盖），但**实测表明内置降雨
  模型在 realistic 强度下不足以驱动走廊切换**（见 §6），仅作敏感性/对照用途，
  **不作为本文"时间感知价值"的主演示机制**；开启后需重跑全部 12 次搜索并重新
  生成 Table 1（与 Exp1 风险场口径将不再一致，需在论文中说明）。
