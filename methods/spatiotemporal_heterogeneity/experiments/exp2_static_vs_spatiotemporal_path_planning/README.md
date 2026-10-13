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

## 6. 结果 (Results，2026-10-13 重跑：暴露口径修正 + 权重重标定)

> ⚠ **口径修正（2026-10-13）**：P_crash 暴露从「整时相 900 s」修正为「格穿越
> 时间 6.8 s」（k ≈ 132，见 `risk_tensor_assembler.build_risk_tensors` docstring），
> w_fatal/w_prop 同比放大 k=132（3960/1584）保持风险-运营权衡 regime；w_noise/
> w_ops 不动。修正后 P_surv 绝对值可进论文正文（旧口径下 P_surv 虚低不可引用）。
> **2026-10-09 之前的历史结果表全部作废，禁止引用**（暴露口径 + 权重均已变更）。

**默认配置（新口径 6.8s 暴露 + 关闭 `localized_hazard`，真实数据口径）统一后评估
（OD (8,61)→(95,5)，60 m 定高，12/12 成功；run.py 2026-10-13 实测）：**

| Time | Method | Length(m) | Hazard H | Survival | Runtime(s) |
|---|---|---|---|---|---|
| 08:00 | Distance-only A* | 5319.3 | 0.0194 | 0.9808 | 2.3 |
| 08:00 | Static-Risk A* | 7219.6 | 0.0170 | 0.9832 | 6.9 |
| 08:00 | Spatiotemporal A* (ours) | 6981.5 | 0.0166 | 0.9835 | 6.9 |
| 12:00 | Distance-only A* | 5319.3 | 0.0168 | 0.9833 | 2.2 |
| 12:00 | Static-Risk A* | 7219.6 | 0.0145 | 0.9856 | 6.7 |
| 12:00 | Spatiotemporal A* (ours) | 6953.3 | 0.0141 | 0.9860 | 6.5 |
| 18:00 | Distance-only A* | 5319.3 | 0.0147 | 0.9854 | 2.3 |
| 18:00 | Static-Risk A* | 7219.6 | 0.0124 | 0.9876 | 6.8 |
| 18:00 | Spatiotemporal A* (ours) | 6953.3 | 0.0121 | 0.9879 | 7.1 |
| 22:00 | Distance-only A* | 5319.3 | 0.0158 | 0.9843 | 2.3 |
| 22:00 | Static-Risk A* | 7219.6 | 0.0135 | 0.9866 | 6.6 |
| 22:00 | Spatiotemporal A* (ours) | 6953.3 | 0.0131 | 0.9870 | 6.6 |

（Fatal/Property/Noise 各时刻指标见 `results/table1_main_results.csv`）

**结论判定（run.py [Conclusion] 实测，真实数据口径）：**
1. $R_{ST} < R_{Static}$ 在 **4/4** 出发时刻成立（每时刻 ΔH = +0.0003~+0.0004，
   mean $\Delta L$(ST vs static) = **−3.59%**）——ST 更短**且**更安全，risk-aware
   trade-off 成立（勿将"更短"当卖点）；
2. **路径决策改变的直接证据**：$D(P_{static},P_{ST})$ = 33.6–50.2 m，path-change rate =
   0.187–0.188（4/4 时刻清晰走廊级改道，扰动 ≥ 0.10）；
3. Static 跨出发时刻 path-change rate ≡ 0.00（sanity 通过：时间平均场无法适应时间）；
   ST 跨时刻偏离 <1 m（该 OD 下 ST 路径本身对出发时刻不敏感，见下方解读注意）；
4. M1 baseline chain 闭合：Distance-only 与风险方法偏离 860 m（change-rate 0.96），
   风险建模确实主导路线选择。

> **⚠ 重要发现 — 暴露口径决定"局部时间风险"能否被路由利用**：本实验曾引入的
> `localized_hazard`（高斯脉冲峰值×12，模拟局地极端天气单体/限飞区）在**旧口径
> （900s 暴露）**下可驱动走廊切换（D=566–590 m，change-rate 0.74）；但合并远程新口径
> （6.8s 暴露，k=132）后，基础 p_crash 被稀释约 132 倍，同一峰值×12 仅把热点
> p_crash 从 ~0.01 拉到 ~0.12，**不足以制造"可过 vs 不可过"的区分**，ST 在活跃时段
> （08/12）与 Static 一样直穿/同绕（D≈6–8 m），情景失效。结论：时空感知能否显现
> 决定性价值，**强烈依赖于风险暴露的时间尺度**——长暴露（旧口径/累计飞行）下局部
> 时间风险可被有效规避；短暴露（逐格穿越）下局部风险被稀释，路由更依赖空间结构。
> **该情景模块保留作可选演示（config 中 `localized_hazard.enabled: true` 即开启），
> 默认关闭、以真实数据口径为主。**

**解读注意**：(a) ST 相对 Static 的风险收益是「安全 + 更短」双赢，但风险增量很小
（~2%，勿将"更短"当卖点）；(b) ST 跨出发时刻的自适应性（同一 ST 方法随 t 改道）在该
OD 下弱（偏离 <1 m），主结论应表述为「时间平均风险图导致次优走廊，时空感知规划选出
更优走廊」，而非「ST 随时刻切换路线」；(c) P_surv 绝对值依赖 λ_base 标定，方法间相对
比较不受影响。
## 7. 备注 (Notes)

- 与 Exp1 的关系：Exp1 证明"风险场时空异质性存在"（机制）；本实验进一步证明
  "这种异质性**值得利用**"（方法收益），是论文证据链的第 2 环；
- 与 Exp3（消融）的分工：本实验只对比三种**目标口径**，不做组件消融；
- `P_surv` 绝对值口径已于 2026-10-13 修正（按格穿越时间计暴露，见 §6 口径声明）；
  修正前旧口径按整时相 900s 暴露放大约 132 倍，旧 P_surv 数字全部作废。修正后
  绝对值依赖 λ_base 标定，方法间相对比较不受影响；
- 降雨可经 `config.yaml` 的 `rain.enabled: true` 一键开启，但**实测内置降雨模型在
  realistic 强度下不足以驱动走廊切换**（见 §6），仅作敏感性/对照用途，不作为本文
  "时间感知价值"的主演示机制；开启后需重跑全部 12 次搜索并重新生成 Table 1；
- `localized_hazard`（极端局地危险事件情景）已改为默认关闭（真实数据口径为主）；
  新口径下该情景失效（见 §6 标注），如需演示脉冲效应可设 `enabled: true` 开启。
