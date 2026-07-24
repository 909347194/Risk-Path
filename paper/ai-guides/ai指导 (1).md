研究**时空异质性**对无人机低空航路风险的影响，核心产出一条四维代价张量 `Cost_total(x,y,z,t)`，供 A* 路径规划使用。



------



## 🏗️ 架构分层（4层）



text

```
data_provision → tensor_engine → algorithms → visualization
data_provision → tensor_engine → algorithms → visualization
```



| 层                 | 职责                                 | 输出维度              |
| ------------------ | ------------------------------------ | --------------------- |
| **data_provision** | 原始 GIS → 对齐 NumPy                | (nx,ny) 或 (nx,ny,nt) |
| **tensor_engine**  | 唯一允许扩展 nz 维，输出 4D 风险张量 | (nx,ny,nz,nt)         |
| **algorithms**     | A* 路径搜索，不做代价生成            | 最优路径              |
| **visualization**  | 网格/张量/路径可视化                 | 图表                  |



------



## 🔬 核心数学模型



### 1. 坠机概率 `dynamic_p_crash.py`

text

```
P_crash = 1 - exp(-λ_base × Φ × Δt)
Φ = f_wind × f_rain × f_obs
P_crash = 1 - exp(-λ_base × Φ × Δt)
Φ = f_wind × f_rain × f_obs
```

- **f_wind**: `exp[k_w × (v/V_limit)^θ]`，风速超限时 → ∞
- **f_rain**: `1 + γ × I²`
- **f_obs**: 城市峡谷放大系数 `1 + K_obs × R_canyon`



### 2. 致死后果 `dynamic_fatality.py`

text

```
E_fatality = S_hit × [ρ_pop × R_f^p(z) + ρ_veh × R_f^v]
E_fatality = S_hit × [ρ_pop × R_f^p(z) + ρ_veh × R_f^v]
```

行人致死率用 sigmoid 模型，取决于撞击能量（与高度相关）。



### 3. 人口潮汐 `spatiotemporal_tidal_model.py`

text

```
ρ(i,t) = ρ_base(i) × [b + Σ W_k × τ_k(t) × A_k(i)]
ρ(i,t) = ρ_base(i) × [b + Σ W_k × τ_k(t) × A_k(i)]
```

5 类 POI（住宅/办公/机构/交通/工业）× 高斯空间衰减 × 时间激活函数。



### 4. 噪声成本 `dynamic_noise.py`

text

```
Cost_noise(x,y,z,t) = I(z) × ρ_pop(x,y,t) × S_landuse(x,y) × T_penalty(x,y,t)
Cost_noise(x,y,z,t) = I(z) × ρ_pop(x,y,t) × S_landuse(x,y) × T_penalty(x,y,t)
```

反平方高度衰减 + S-T 敏感度矩阵（住宅夜间 ×10，学校全天 ×10）。



### 5. 财产损失 `static_obstacle.py`

text

```
E_property = V_building × η_damage
V_building ~ LogNormal(μ + α·ln(H), σ²)
E_property = V_building × η_damage
V_building ~ LogNormal(μ + α·ln(H), σ²)
```



------



## 🧠 A* 算法设计 (`astar_4d.py`)



**状态向量**`SearchNode`：

python

```
state = {
    'cum_distance': float,      # 累计距离
    'cum_time': float,          # 累计时间
    'absolute_time': float,     # 绝对时间（秒）
    'cumulative_hazard': float, # H = -ln(P_surv)，避免数值下溢
    'p_survival': float,        # exp(-H)
    'cum_fatality': float,      # 累计致死风险
    'cum_property': float,      # 累计财产损失
    'cum_noise': float,         # 累计噪声成本
    'cum_objective': float,     # 归一化目标函数 J
}
state = {
    'cum_distance': float,      # 累计距离
    'cum_time': float,          # 累计时间
    'absolute_time': float,     # 绝对时间（秒）
    'cumulative_hazard': float, # H = -ln(P_surv)，避免数值下溢
    'p_survival': float,        # exp(-H)
    'cum_fatality': float,      # 累计致死风险
    'cum_property': float,      # 累计财产损失
    'cum_noise': float,         # 累计噪声成本
    'cum_objective': float,     # 归一化目标函数 J
}
```



**节点扩展核心逻辑**：

- 时间推进：`dt = dist / uav_speed`（物理距离驱动，非固定步长）
- 存活概率：**乘法累积**（用 cumulative_hazard 对数空间避免下溢）
- 致死/财产：`δ = P_surv × P_crash × consequence`（条件期望）
- 噪声：`δ = P_surv × noise × dt`（连续暴露）
- 硬约束剪枝：存活率阈值 + 电池续航



**Label-Setting 机制**：同一空间位置 (x,y,z) 可存在多个非支配标签 (t, H, J)，支持 Pareto 最优。



**归一化单步代价**（论文 §3.4）：

text

```
δJ = w_f×(δC_f/Ω_f) + w_p×(δC_p/Ω_p) + w_n×(δC_n/Ω_n) + w_d×(d/d_max)
δJ = w_f×(δC_f/Ω_f) + w_p×(δC_p/Ω_p) + w_n×(δC_n/Ω_n) + w_d×(d/d_max)
```



------



## 📊 实验结果（微观 40×40 网格）



| 实验           | 关键发现                                                    |
| -------------- | ----------------------------------------------------------- |
| **时间节律**   | 18:00 晚高峰路径更长（+18m），因风+雨导致 P_crash 高达 0.38 |
| **微气象耦合** | TD-RiskA* 绕行更远但累积伤亡降低 61%                        |
| **帕累托权衡** | 归一化后目标函数 J 随 w_noise 增大而减小                    |
| **剪枝效率**   | 所有策略找到相同最优路径，验证剪枝不损失最优性              |



------



## 📁 关键文件索引



| 功能         | 路径                                               |
| ------------ | -------------------------------------------------- |
| 网格系统     | `src/tensor_engine/grid_system.py`                 |
| 坠机概率     | `src/tensor_engine/dynamic_p_crash.py`             |
| 致死模型     | `src/tensor_engine/dynamic_fatality.py`            |
| 噪声成本     | `src/tensor_engine/dynamic_noise.py`               |
| 人口潮汐     | `src/data_provision/spatiotemporal_tidal_model.py` |
| 数据管线     | `src/data_provision/pipeline.py`                   |
| 环境张量容器 | `src/algorithms/env_tensor.py`                     |
| A* 算法      | `src/algorithms/a_star/astar_4d.py`                |
| 配置文件     | `configs/common.yaml`                              |
| 实验脚本     | `experiments/exp1/`                                |



有什么具体问题或需要深入分析的部分？

## 📋 汇报大纲



text

```
一、研究背景与问题
二、系统架构设计
三、核心模型实现
    3.1 四维网格系统
    3.2 动态坠机概率模型（Cox PH）
    3.3 致死后果模型
    3.4 人口潮汐模型
    3.5 噪声社会敏感度模型（S-T矩阵）
    3.6 财产损失模型
四、TD-RiskA* 算法设计
    4.1 状态向量设计
    4.2 节点扩展逻辑
    4.3 Label-Setting 剪枝机制
    4.4 归一化单步代价
五、合成数据与实验平台
六、微观机制验证实验（4组）
    6.1 实验1：时间节律自适应性
    6.2 实验2：微气象-地形耦合避让
    6.3 实验3：噪声-安全帕累托权衡
    6.4 实验4：多标签剪枝效率
七、下一步工作计划
一、研究背景与问题
二、系统架构设计
三、核心模型实现
    3.1 四维网格系统
    3.2 动态坠机概率模型（Cox PH）
    3.3 致死后果模型
    3.4 人口潮汐模型
    3.5 噪声社会敏感度模型（S-T矩阵）
    3.6 财产损失模型
四、TD-RiskA* 算法设计
    4.1 状态向量设计
    4.2 节点扩展逻辑
    4.3 Label-Setting 剪枝机制
    4.4 归一化单步代价
五、合成数据与实验平台
六、微观机制验证实验（4组）
    6.1 实验1：时间节律自适应性
    6.2 实验2：微气象-地形耦合避让
    6.3 实验3：噪声-安全帕累托权衡
    6.4 实验4：多标签剪枝效率
七、下一步工作计划
```



------



## 📝 各部分详细内容



### 一、研究背景与问题



> **核心问题**：时空异质性（人口潮汐、气象变化、噪声昼夜差异）如何影响无人机低空航路的风险分布？如何在路径规划中同时考虑安全性、财产损失和社会噪声滋扰？



**研究目标**：

- 构建四维风险代价场 `Cost_total(x,y,z,t)`
- 设计能感知时空异质性的路径规划算法 TD-RiskA*
- 在安全、财产、噪声三个维度上实现 Pareto 最优



------



### 二、系统架构设计



**四层分层架构**：



| 层         | 模块              | 职责                      | 输出维度              |
| ---------- | ----------------- | ------------------------- | --------------------- |
| ① 数据供应 | `data_provision/` | 原始 GIS → 对齐 NumPy     | (nx,ny) 或 (nx,ny,nt) |
| ② 张量引擎 | `tensor_engine/`  | 风险分量计算 + 高度维扩展 | (nx,ny,nz,nt)         |
| ③ 路径规划 | `algorithms/`     | A* 搜索 + Label-Setting   | 最优路径              |
| ④ 可视化   | `visualization/`  | 网格/张量/路径可视化      | 图表                  |



**关键设计约束**：

- 高度维 `nz` 仅在 `tensor_engine` 中扩展，其他层只处理 (nx,ny) 或 (nx,ny,nt)
- 合成/真实数据一键切换：`set_data_type('synthetic')` 或 `'real'`
- 配置驱动：所有参数从 `configs/*.yaml` 读取，不在代码中硬编码



------



### 三、核心模型实现



#### 3.1 四维网格系统 `GridSystem`



| 参数     | 微观验证           | 宏观案例          |
| -------- | ------------------ | ----------------- |
| 空间范围 | 400m × 400m × 120m | 5km × 5km × 120m  |
| 网格维度 | 40 × 40 × 12       | 100 × 100 × 12    |
| 分辨率   | 10m × 10m × 10m    | 50m × 50m × 10m   |
| 时间维度 | 96 步（15min/步）  | 96 步（15min/步） |



坐标系：X/Y 从 0 开始（GIS 标准），Z 从 dz 开始（安全高度偏移）。



#### 3.2 动态坠机概率模型



基于 **Cox 比例风险模型**：



text

```
P_crash(x,y,z,t) = 1 - exp(-λ_base × Φ(x,y,z,t) × Δt)
Φ = f_wind × f_rain × f_obs
P_crash(x,y,z,t) = 1 - exp(-λ_base × Φ(x,y,z,t) × Δt)
Φ = f_wind × f_rain × f_obs
```



三个风险因子：

- **风场**`f_wind = exp[k_w × (v/V_limit)^θ]`：风速超限 → ∞（禁飞）
- **降雨**`f_rain = 1 + γ × I²`：线性增强
- **城市峡谷**`f_obs = 1 + K_obs × R_canyon`：SVF + 高度比 + 建筑邻近度加权



#### 3.3 致死后果模型



text

```
E_fatality(x,y,z,t) = S_hit × [ρ_pop(x,y,t) × R_f^p(z) + ρ_veh(x,y,t) × R_f^v]
E_fatality(x,y,z,t) = S_hit × [ρ_pop(x,y,t) × R_f^p(z) + ρ_veh(x,y,t) × R_f^v]
```



- 行人致死率 `R_f^p`：sigmoid 函数，取决于撞击能量 `E_imp = ½mv²`
- 车辆致死率 `R_f^v`：统计常数 0.01



#### 3.4 人口潮汐模型



text

```
ρ(i,t) = ρ_base(i) × [b + Σ_k W_k × τ_k(t) × A_k(i)]
ρ(i,t) = ρ_base(i) × [b + Σ_k W_k × τ_k(t) × A_k(i)]
```



- 5 类 POI：住宅/办公/机构/交通/工业
- 空间衰减：高斯核卷积（FFT 加速）
- 时间激活：混合高斯/梯形/逻辑函数模拟昼夜节律



#### 3.5 噪声社会敏感度模型（S-T 矩阵）



text

```
Cost_noise(x,y,z,t) = I(z) × ρ_pop(x,y,t) × S_landuse(x,y) × T_penalty(x,y,t)
Cost_noise(x,y,z,t) = I(z) × ρ_pop(x,y,t) × S_landuse(x,y) × T_penalty(x,y,t)
```



**S-T 敏感度矩阵**（论文 Table 6）：



| 土地类别                | S 敏感度 | T_day    | T_night  |
| ----------------------- | -------- | -------- | -------- |
| 自然/开放               | 0.0      | 1.0      | 1.0      |
| 工业/物流               | 0.2      | 1.0      | 0.5      |
| 基础设施/交通           | 0.5      | 1.0      | 1.5      |
| 商业/行政               | 0.5      | 1.0      | 1.5      |
| 住宅                    | 1.0      | 1.5      | **10.0** |
| 高敏感保护（学校/医院） | 2.0      | **10.0** | **10.0** |



高度衰减：`I(z) = L_ref / (z² + d²)`（反平方律）



#### 3.6 财产损失模型



text

```
E_property = V_building × η_damage
V_building ~ LogNormal(μ + α·ln(H), σ²)
E_property = V_building × η_damage
V_building ~ LogNormal(μ + α·ln(H), σ²)
```



建筑价值通过对数正态分布估算，与高度正相关。



------



### 四、TD-RiskA* 算法设计



#### 4.1 状态向量



每个搜索节点携带完整的物理累积状态：



python

```
state = {
    'cum_distance': float,       # 累计飞行距离 (m)
    'cum_time': float,           # 累计飞行时间 (s)
    'absolute_time': float,      # 绝对时间（秒）
    'cumulative_hazard': float,  # H = -ln(P_surv)，对数空间避免下溢
    'p_survival': float,         # exp(-H)，存活概率
    'cum_fatality': float,       # 累计致死风险
    'cum_property': float,       # 累计财产损失
    'cum_noise': float,          # 累计噪声成本
    'cum_objective': float,      # 归一化目标函数 J
}
state = {
    'cum_distance': float,       # 累计飞行距离 (m)
    'cum_time': float,           # 累计飞行时间 (s)
    'absolute_time': float,      # 绝对时间（秒）
    'cumulative_hazard': float,  # H = -ln(P_surv)，对数空间避免下溢
    'p_survival': float,         # exp(-H)，存活概率
    'cum_fatality': float,       # 累计致死风险
    'cum_property': float,       # 累计财产损失
    'cum_noise': float,          # 累计噪声成本
    'cum_objective': float,      # 归一化目标函数 J
}
```



#### 4.2 节点扩展逻辑



text

```
1. 时间推进：dt = dist / uav_speed（物理距离驱动，非固定步长）
2. 从 EnvTensor 提取邻居格点的风险分量
3. 累积风险更新：
   - H_new = H_old + h_step           （对数空间加法累积）
   - P_survival = exp(-H)             （存活概率）
   - δ_fatality = P_surv × P_crash × E_fatality  （条件期望）
   - δ_property = P_surv × P_crash × E_property
   - δ_noise = P_surv × R_noise × dt  （连续暴露）
4. 硬约束剪枝：
   - P_survival < 阈值 → 禁飞
   - cum_time > 电池续航 → 剪枝
1. 时间推进：dt = dist / uav_speed（物理距离驱动，非固定步长）
2. 从 EnvTensor 提取邻居格点的风险分量
3. 累积风险更新：
   - H_new = H_old + h_step           （对数空间加法累积）
   - P_survival = exp(-H)             （存活概率）
   - δ_fatality = P_surv × P_crash × E_fatality  （条件期望）
   - δ_property = P_surv × P_crash × E_property
   - δ_noise = P_surv × R_noise × dt  （连续暴露）
4. 硬约束剪枝：
   - P_survival < 阈值 → 禁飞
   - cum_time > 电池续航 → 剪枝
```



#### 4.3 Label-Setting 剪枝



- 同一空间位置 (x,y,z) 可存在多个非支配标签 (t, H, J)
- 支配关系：标签 A 支配标签 B，当且仅当 A.t ≤ B.t 且 A.H ≤ B.H 且 A.J ≤ B.J
- 每个格点最多保留 `max_labels` 个标签（默认 4）



#### 4.4 归一化单步代价（论文 §3.4）



text

```
δJ = w_f × (δC_f / Ω_f) + w_p × (δC_p / Ω_p) + w_n × (δC_n / Ω_n) + w_d × (d / d_max)
δJ = w_f × (δC_f / Ω_f) + w_p × (δC_p / Ω_p) + w_n × (δC_n / Ω_n) + w_d × (d / d_max)
```



其中 Ω 为各分量最大值，实现无量纲归一化。



------



### 五、合成数据与实验平台



**合成城市生成器**（`utils/synthetic_data_factory/`）：

- 生成顺序：landuse → road → building → POI → population → weather → OD
- 支持 seed 确定性复现
- 输出 7 类数据：土地利用、建筑高度、道路网络、POI、人口、气象（风/雨）、OD 对



**数据管线**（`data_provision/pipeline.py`）：

- 7 个处理阶段一键运行
- 自动合成/真实路径切换



------



### 六、微观机制验证实验（4组）



**实验场景**：40m × 40m × 12 层 × 24 时间步，OD = (2,2) → (37,37)，UAV 速度 10 m/s



#### 实验 1：时间节律自适应性



验证同一 OD 对在不同出发时刻生成不同路径。



| 出发时刻            | 路径长度 | 存活概率  | 累积噪声   | 搜索节点 | 运行时间  |
| ------------------- | -------- | --------- | ---------- | -------- | --------- |
| 08:00（早高峰）     | 495m     | 0.187     | 0.0025     | 179      | 7ms       |
| 12:00（午间）       | 495m     | 0.058     | 0.0021     | 179      | 8ms       |
| **18:00（晚高峰）** | **513m** | **0.011** | 0.0016     | **4864** | **638ms** |
| 22:00（夜间）       | 495m     | **0.259** | **0.0040** | 179      | 7ms       |



**结论**：

- 18:00 晚高峰路径更长（+18m），因中心区域风+雨导致 P_crash 高达 0.38，算法主动绕行
- 22:00 夜间存活概率最高（无风雨），但噪声成本最高（住宅区 T_penalty ×10）
- 搜索节点从 179 激增到 4864，说明晚高峰场景下路径选择空间显著增大



#### 实验 2：微气象-地形耦合避让



| 条件     | 算法          | 路径长度 | 存活概率 | 累积伤亡    | 运行时间 |
| -------- | ------------- | -------- | -------- | ----------- | -------- |
| Calm     | Distance-only | 495m     | 0.270    | 0.00096     | 7ms      |
| Calm     | TD-RiskA*     | 495m     | 0.270    | 0.00096     | 7ms      |
| **Wind** | Distance-only | 559m     | 0.013    | **0.00226** | 866ms    |
| **Wind** | TD-RiskA*     | **577m** | 0.014    | **0.00089** | 2242ms   |
| Rain     | Distance-only | 495m     | 0.106    | 0.00103     | 7ms      |
| Rain     | TD-RiskA*     | 495m     | 0.106    | 0.00103     | 7ms      |



**结论**：

- **风场耦合**：TD-RiskA* 绕行更远（577m vs 559m），但累积伤亡**降低 61%**（0.00089 vs 0.00226）
- 平静/降雨条件下两种算法路径相同（风险未超过阈值）
- 风场是最显著的风险因子（f_wind 在 V_limit 附近指数增长）



#### 实验 3：噪声-安全帕累托权衡



| 权重配置 | w_noise | w_distance | 路径长度 | 存活概率 | 累积噪声 | 目标函数 J |
| -------- | ------- | ---------- | -------- | -------- | -------- | ---------- |
| w_n=0.05 | 0.05    | 0.65       | 495m     | 0.269    | 0.0041   | 18.58      |
| w_n=0.15 | 0.15    | 0.55       | 495m     | 0.269    | 0.0041   | 15.73      |
| w_n=0.30 | 0.30    | 0.40       | 495m     | 0.269    | 0.0041   | 11.44      |
| w_n=0.50 | 0.50    | 0.20       | 495m     | 0.269    | 0.0041   | 5.72       |



**结论**：

- 归一化后目标函数 J 随 w_noise 增大而单调减小（符合预期）
- 当前场景路径未改变（噪声贡献 ~0.004 vs 距离贡献 ~28），需更强的空间对比
- 下一步：设计穿过住宅区 vs 绕行的场景以显现 Pareto 前沿



#### 实验 4：多标签剪枝效率



| 策略       | max_labels | 路径长度 | 目标函数 J | 运行时间 | 搜索节点 |
| ---------- | ---------- | -------- | ---------- | -------- | -------- |
| No Pruning | 50         | 495m     | 11.44      | 8.0ms    | 179      |
| Strict     | 1          | 495m     | 11.44      | 7.6ms    | 179      |
| Proposed   | 4          | 495m     | 11.44      | 7.1ms    | 179      |
| Proposed   | 8          | 495m     | 11.44      | 7.1ms    | 179      |
| Proposed   | 16         | 495m     | 11.44      | 6.5ms    | 179      |



**消融实验**（max_labels 从 1 到 50）：



| max_labels | 目标函数 J | 运行时间 | 搜索节点 |
| ---------- | ---------- | -------- | -------- |
| 1          | 11.44      | 7.6ms    | 179      |
| 4          | 11.44      | 6.6ms    | 179      |
| 16         | 11.44      | 7.1ms    | 179      |
| 50         | 11.44      | 7.9ms    | 179      |



**结论**：

- 所有策略均找到**相同最优路径**（495m, J=11.44），验证剪枝不损失最优性
- k=4 即可达到最优（6.6ms），说明该场景标签冲突少
- 搜索空间较小（40×40），剪枝效果需在宏观场景进一步验证



------



### 七、下一步工作计划



| 阶段     | 任务                                      | 时间   |
| -------- | ----------------------------------------- | ------ |
| **短期** | 宏观城区案例研究（100×100 网格）          | 1-2 周 |
| **短期** | 设计强噪声对比场景（住宅穿越 vs 绕行）    | 1 周   |
| **中期** | 可视化增强：3D 路径 + 沿途风险累积曲线    | 1 周   |
| **中期** | 敏感性分析：权重组合 → Pareto 前沿图      | 1 周   |
| **中期** | 真实数据集成（WorldPop + OSM + ERA5）     | 2 周   |
| **长期** | 论文实验章节撰写                          | 2-4 周 |
| **长期** | 算法优化：NumPy 向量化 / bidirectional A* | 2 周   |



------



### 🎯 汇报时可展示的图片（共 12 张）



| 编号 | 图片                                 | 用途               |
| ---- | ------------------------------------ | ------------------ |
| 1    | `grid_3d_matplotlib.png`             | 网格系统 3D 结构   |
| 2    | `00_composite_overview.png`          | 合成城市总览       |
| 3    | `01_landuse_map.png`                 | 土地利用分类       |
| 4    | `03_building_heights.png`            | 建筑高度分布       |
| 5    | `05_population_density.png`          | 人口密度           |
| 6    | `07_wind_field.png`                  | 风场分布           |
| 7    | `08_rain_data.png`                   | 降雨分布           |
| 8    | `fig_paths_2d.png`（exp1）           | 时间节律路径对比   |
| 9    | `fig_cumulative_curves.png`（exp1）  | 累积风险曲线       |
| 10   | `fig_paths_comparison.png`（exp2）   | 微气象耦合路径对比 |
| 11   | `fig_pareto_scatter.png`（exp3）     | 帕累托散点图       |
| 12   | `fig_runtime_comparison.png`（exp4） | 剪枝效率对比       |



------



### 💡 汇报建议



1. 1.**开场**用一张架构图 + 数据流图说清楚整体设计（2 min）
2. 2.**核心贡献**聚焦在状态向量设计 + Label-Setting 机制（这是论文创新点）（5 min）
3. 3.**实验部分**用实验 2（风场耦合，伤亡降 61%）作为最有力的论据（3 min）
4. 4.**诚实说明局限**：当前网格较小（40×40），剪枝效果不显著；噪声 Pareto 前沿还需更强的场景（1 min）
5. 5.**下一步计划**重点提宏观案例 + 真实数据（1 min）



需要我直接生成 PPT 或者把这份大纲写成文件吗？