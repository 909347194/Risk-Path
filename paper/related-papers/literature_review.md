# 相关文献综述

> 检索时间：2026-07-17  
> 检索关键词：UAV path planning, spatiotemporal risk, third-party risk, urban low-altitude, noise, Cox PHM, time-dependent A*

---

## 一、TPR 量化评估与路径规划

### 1.1 Pang et al. (2022) — 最直接竞争对手

**标题：** UAV path optimization with an integrated cost assessment model considering third-party risks in metropolitan environments

**期刊：** Reliability Engineering & System Safety (SCI Q1 Top, IF=8.1)

**作者：** Pang B Z, Hu X T, Dai W, Low K H（南洋理工大学）

**内容：**
- 首次建立**综合 TPR 模型**，包含三个维度：
  - 致死风险（fatality risk）：P_crash × N_hit × R_f
  - 财产损失（property damage）：建筑高度 × 横截面积
  - 噪声影响（noise impact）：基于距离衰减
- 提出 Min-cost A* 算法进行路径规划
- 使用改进 Floyd 算法平滑路径
- 实验结果：风险成本降低 42.64%~44.15%（95% 置信水平）

**局限性：**
- **静态风险场**：P_crash 是常数，不随时间/环境变化
- 人口密度是静态的
- 噪声模型仅基于距离衰减，无时间/土地利用敏感度

**与我们的关系：**
> Pang (2022) 建立了 TPR 的"静态版"，本文建立了 TPR 的"物理驱动动态版"。我们的贡献是将 P_crash 从常数扩展为 Cox PHM 的环境函数，将人口从静态扩展为潮汐模型，将噪声从距离衰减扩展为 S-T 敏感度矩阵。

---

### 1.2 Tang et al. (2023)

**标题：** UAV path planning based on third-party risk modeling

**期刊：** Scientific Reports (SCI Q2, IF=4.6)

**作者：** Tang H Y, Zhu Q, Qin B, Song R Y, Li Z

**内容：**
- 建立第三方风险模型：障碍物风险 + 死亡风险 + 财产损失风险
- 提出 Min-cost A* 算法
- 实验在 3D 城市场景中验证

**局限性：**
- **静态风险**，无时间维度
- **无噪声建模**
- 风险模型较简化（无微气象因子）

**与我们的关系：**
> Tang (2023) 的 TPR 模型比 Pang (2022) 更简化，且无噪声维度。我们的工作在风险建模维度上更全面（致死+财产+噪声），且引入了时间异质性。

---

## 二、动态风险路径规划

### 2.1 Pang et al. (2024) — 动态风险方向的直接竞争

**标题：** Stochastic route optimization under dynamic ground risk uncertainties for safe drone delivery operations

**期刊：** Transportation Research Part E (SCI Q1 Top, IF=10.0)

**作者：** Pang B Z, Hu X T, Dai W（南洋理工大学）

**内容：**
- 引入**动态地面风险**，考虑风险的不确定性
- 采用**两阶段随机优化**框架
- 第一阶段：确定性路径规划
- 第二阶段：根据实际风险调整

**局限性：**
- **无噪声建模**
- **无微气象因子**（风/雨/建筑峡谷）
- **无潮汐人口模型**
- 风险的"动态"是指不确定性（随机扰动），不是物理机制驱动的时变

**与我们的关系：**
> Pang (2024) 在"动态"方向上迈出了重要一步，但其动态性来自随机扰动而非物理机制。我们的动态性来自 Cox PHM（微气象耦合）和潮汐模型（人口节律），是物理可解释的。

---

### 2.2 4D Space-Time A* (2026) — 4D 时空框架的竞争

**标题：** A 4D space–time network model for UAV path planning with time-variant risk

**期刊：** Transportation Research Part C (SCI Q1 Top, IF=8.3)

**发表：** 2026-07

**内容：**
- 提出**时间分层四维时空 A* 算法**（TL-FDSTA*）
- 使用电子警察监控数据刻画时变风险不确定性
- 数据驱动方法

**局限性：**
- **无物理风险建模**（直接用数据，不建模为什么风险会变）
- **无噪声建模**
- **无微气象因子**
- 依赖特定数据源（电子警察）

**与我们的关系：**
> TRC (2026) 也使用 4D 时空 A*，但其风险来源是交通监控数据，缺乏物理机制支撑。我们的优势是：(1) 物理机制驱动的坠机概率模型（Cox PHM），(2) 多维风险（致死+财产+噪声），(3) 不依赖特定数据源，可合成/真实数据切换。

---

## 三、城市低空风险场

### 3.1 Wu et al. (2026) — 风险场方法

**标题：** 基于低空风险场的三维航迹规划

**期刊：** 北京理工大学学报 (EI)

**作者：** 吴炎烜, 付伊凡, 罗旭东, 孙浩南, 厉昊

**内容：**
- 构建融合**静态势能场与动态动能场**的三维风险模型
- 提出 4 级优先级响应机制
- 三维网格离散化 + 实时风险计算
- 实验：预测时间 1.5s 时，平均碰撞次数 0.1 次

**局限性：**
- **实时反应式**，不是预先规划
- 风险场是连续场（势能+动能），不是离散张量
- 无噪声建模
- 无潮汐人口

**与我们的关系：**
> Wu (2026) 的风险场方法适用于在线避障，但不适用于离线航路规划（我们的场景）。我们的 TD-RiskA* 是规划阶段的全局优化，不是飞行中的实时反应。

---

### 3.2 Gao et al. (2026) — 算法改进方向

**标题：** Urban low-altitude UAV path planning by fusing an enhanced A* algorithm with an adaptive artificial potential field method

**期刊：** Scientific Reports (SCI Q2, IF=4.6)

**内容：**
- 多阶段轨迹规划：A*（全局）+ APF（局部避障）
- 3D 体素化城市空域模型
- 双半径安全避障模型 + 动态步长调整
- B 样条平滑
- 结果：计算时间降低 36%，路径长度降低 18%

**局限性：**
- **无风险建模**，纯算法优化
- 无噪声/致死/财产等 TPR 评估
- 无时间维度

**与我们的关系：**
> Gao (2026) 是纯算法改进，不涉及风险建模。我们的贡献在风险建模层面，算法层面用的是标准 A* 的时间依赖扩展。

---

## 四、噪声约束路径规划

### 4.1 噪声相关专利/方法 (2025-2026)

**专利 1：** 一种多无人机低噪声路径规划方法及系统 (2025)
- 将噪声融入人工势场算法
- 噪声特性转化为排斥力机制
- 实时路径规划

**专利 2：** 一种考虑噪声的城市低空无人机路径优化方法 (2025)
- 构建多约束路径规划模型
- 考虑噪声敏感区域

**与我们的关系：**
> 现有噪声相关工作多将噪声作为**硬约束**（不超过阈值）或**简单惩罚项**。我们的创新是：(1) 基于声学能量守恒的噪声成本模型（非 dB 对数尺度），(2) S-T 敏感度矩阵（土地利用×时间段），(3) 噪声作为多目标优化的一个维度（与致死/财产/距离并列）。

---

## 五、多智能体/分布式路径规划

### 5.1 Nordström et al. (2025)

**标题：** A Time-dependent Risk-aware distributed Multi-Agent Path Finder based on A*

**期刊：** arXiv (Submitted to IROS 2025)

**内容：**
- A*+T 算法：分布式多智能体路径规划
- 时间依赖的风险层
- 动态障碍物的速度/轨迹预测

**与我们的关系：**
> Nordström (2025) 的"时间依赖"是指动态障碍物的时间预测，不是环境风险的时空异质性。我们的"时间依赖"是指同一位置在不同时刻有不同的坠机概率/人口密度/噪声敏感度。

---

## 六、综述/框架

### 6.1 测绘地理信息支撑低空经济 (2026)

**标题：** 测绘地理信息如何支撑低空经济：风险量化、航路规划、飞行导航与低空应用

**期刊：** 测绘通报 (EI)

**作者：** 唐炉亮等（武汉大学）

**内容：**
- 系统梳理低空飞行风险来源
- SORA 语义模型演进
- 实景三维赋能低空风险量化
- 单机航路→多机航路网→低空公共航路网

**与我们的关系：**
> 这篇综述确认了"风险量化 + 航路规划"是低空经济的核心技术问题。我们的工作在这个框架内，聚焦于 TPR 的时空异质性建模。

---

## 七、竞争格局总结

```
                     静态风险          动态风险
                   ┌──────────────┬──────────────┐
  单维（致死）      │ Tang (2023)  │              │
                   ├──────────────┼──────────────┤
  双维（致死+财产） │              │              │
                   ├──────────────┼──────────────┤
  三维（+噪声）     │ Pang (2022)  │  ★ 本文 ★    │
                   ├──────────────┼──────────────┤
  4D 时空框架       │              │ TRC (2026)   │
                   └──────────────┴──────────────┘
```

**本文占据的生态位：三维 TPR + 动态风险 + 物理机制驱动**

这是现有文献中的空白点：
- Pang (2022)：三维 TPR，但静态
- Pang (2024)：动态风险，但无噪声/微气象
- TRC (2026)：4D 时空，但无物理建模/无噪声
- **本文：三维 TPR + Cox PHM 微气象耦合 + 潮汐人口 + S-T 噪声矩阵**

---

## 参考文献列表

1. Pang B Z, Hu X T, Dai W, et al. UAV path optimization with an integrated cost assessment model considering third-party risks in metropolitan environments[J]. Reliability Engineering & System Safety, 2022, 222: 108399.
2. Pang B Z, Hu X T, Dai W. Stochastic route optimization under dynamic ground risk uncertainties for safe drone delivery operations[J]. Transportation Research Part E, 2024, 192: 103717.
3. Tang H Y, Zhu Q, Qin B, et al. UAV path planning based on third-party risk modeling[J]. Scientific Reports, 2023, 13: 22259.
4. A 4D space–time network model for UAV path planning with time-variant risk[J]. Transportation Research Part C, 2026.
5. Wu Y X, Fu Y F, Luo X D, et al. 基于低空风险场的三维航迹规划[J]. 北京理工大学学报, 2026.
6. Gao W, Li L L, Pang D Y. Urban low-altitude UAV path planning by fusing an enhanced A* algorithm with an adaptive artificial potential field method[J]. Scientific Reports, 2026, 16: 18275.
7. Nordström S, Bai Y, Lindqvist B, et al. A Time-dependent Risk-aware distributed Multi-Agent Path Finder based on A*[J]. arXiv:2504.19593, 2025.
8. 唐炉亮等. 测绘地理信息如何支撑低空经济：风险量化、航路规划、飞行导航与低空应用[J]. 测绘通报, 2026.
