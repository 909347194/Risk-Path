# Manuscript2 当前推荐算法设计：在线时间采样的 TD-RiskA\*

本文档给出当前最建议用于论文表述与代码实现的算法设计思路。核心原则是：**不显式构造完整四维时空图，而是在三维空间搜索过程中，根据路径累计飞行时间在线采样动态风险张量**。这样既保留“时空动态风险”的论文创新点，又避免完整 `(x,y,z,t)` 细栅格搜索导致的维度爆炸。

## 我的建议

我建议你的论文从\*\*"四维离散张量搜索"**调整为**"三维空间搜索 + 连续时间状态传播 + 在线时空风险采样"\*\*。这样有几个优势：

1. **理论层面**：风险仍然定义在四维时空域，因此你的"动态风险建模"创新点完全保留。
2. **算法层面**：搜索图始终只有三维空间拓扑，不会因为时间离散导致状态空间指数增长。
3. **状态演化层面**：到达时间 ti已经是状态向量 Si=[pi,ti,Ψi]的组成部分，在线采样与马尔可夫状态传播天然一致，不需要额外修改推导。
4. **工程层面**：人口、交通、天气等数据本身往往以分钟级、5分钟级或小时级更新，在线插值采样比预构建海量四维网格更加符合真实数据组织方式。

从整体来看，这种设计比显式构建完整四维搜索图更加成熟，也更符合现代**time-dependent path planning**的实现思路，同时不会削弱你论文关于时空动态风险建模的贡献。

## 1. 问题本质

本文研究的是给定 OD 对与出发时刻下的城市低空无人机三维航路规划问题。环境风险随时间变化，因此路径代价不是静态二维或三维地图上的固定值，而是时间依赖函数：

```text
Risk = Risk(x, y, z, t)
```

如果直接把空间和时间全部展开，搜索节点为：

```text
(x, y, z, t)
```

则节点规模约为：

```text
O(nx * ny * nz * nt)
```

城市尺度下计算量会急剧膨胀。因此本文算法不采用完整四维暴力搜索，而采用**时间依赖三维搜索**：

```text
节点位置: (x, y, z)
节点状态: 到达该点的时间 t_i 与累计风险
风险查询: Risk(x, y, z, t_i)
```

也就是说，时间不是被完整枚举的第四个图维度，而是路径搜索过程中的状态属性。

## 2. 算法名称建议

建议论文中将算法称为：

```text
Time-Dependent Risk-aware A* (TD-RiskA*)
```

中文可称为：

```text
时间依赖风险感知 A* 算法
```

更完整的技术描述为：

> 本文提出一种在线时间采样的 TD-RiskA\* 算法。该算法在三维栅格空间中进行邻域搜索，并在每次扩展候选节点时，根据当前路径累计飞行时间计算候选节点的实际到达时刻，从动态风险张量中采样对应时刻的风险值，从而实现时间依赖风险感知路径规划。

## 3. 输入数据

算法输入包括：

```text
start = (x_start, y_start, z_start)
goal = (x_goal, y_goal, z_goal)
t_departure
v_uav
grid
dynamic risk tensors
constraints
weights
```

其中动态风险张量建议包括：

| 变量                   | 含义                     |
| ---------------------- | ------------------------ |
| `hazard_rate(x,y,z,t)` | 局部坠机危险率           |
| `e_fatality(x,y,z,t)`  | 坠机后造成的期望伤亡后果 |
| `e_property(x,y,z)`    | 坠机后造成的财产损失后果 |
| `r_noise(x,y,z,t)`     | 单位时间噪声社会影响率   |
| `obstacle(x,y,z)`      | 建筑、禁飞区等硬障碍     |

若当前代码暂时只有 `p_crash(x,y,z,t)`，也可以先使用 `p_crash` 近似，但更严谨的实现应使用 `hazard_rate`，并在边扩展时根据飞行耗时计算单步坠机概率。

## 4. 状态定义

搜索节点建议定义为：

```text
S_i = (p_i, t_i, H_i, C_f_i, C_p_i, C_n_i, L_i, J_i)
```

其中：

| 符号                  | 含义                                    |
| --------------------- | --------------------------------------- |
| `p_i = (x_i,y_i,z_i)` | 当前三维栅格位置                        |
| `t_i`                 | 到达当前点的绝对时间                    |
| `H_i`                 | 累计失效风险强度，`H_i = -ln(P_surv_i)` |
| `C_f_i`               | 累计致死风险成本                        |
| `C_p_i`               | 累计财产损失风险成本                    |
| `C_n_i`               | 累计噪声社会影响成本                    |
| `L_i`                 | 累计路径长度                            |
| `J_i`                 | 累计归一化综合目标值                    |

推荐使用 `H_i` 而不是直接保存 `P_surv_i`，因为 `H_i` 是加法量，数值更稳定：

```text
P_surv_i = exp(-H_i)
```

生存概率约束可以写成：

```text
H_i <= -ln(P_th)
```

## 5. 邻域扩展逻辑

算法在三维空间中采用 26 邻域扩展。对于当前节点 `S_i`，候选邻居集合为：

```text
N_26(p_i) = {
  (x_i + dx, y_i + dy, z_i + dz)
  | dx,dy,dz in {-1,0,1}, not all zero
}
```

对每一个候选邻居 `p_j`，先进行硬约束检查：

```text
1. 是否越界
2. 是否为建筑或禁飞障碍
3. 是否违反最低/最高飞行高度
4. 是否违反最大爬升/下降速度
5. 是否超过最大航程或最大飞行时间
```

若任一硬约束不满足，该邻居直接丢弃。

## 6. 在线时间采样

对于通过硬约束的候选邻居，计算从当前节点飞到该邻居的距离与耗时：

```text
d_ij = ||p_j - p_i||
Delta t_ij = d_ij / v_uav
t_j = t_i + Delta t_ij
```

然后使用到达时间 `t_j` 查询动态风险张量：

```text
hazard_rate_j = hazard_rate(p_j, t_j)
e_fatality_j = e_fatality(p_j, t_j)
e_property_j = e_property(p_j)
r_noise_j = r_noise(p_j, t_j)
```

这里的关键点是：**风险不是用出发时刻固定地图，也不是预先展开所有时间层，而是在每次到达候选点时按实际到达时间查询。**

如果动态张量只在离散时间片上定义，可采用：

```text
t_idx = floor(t_j / Delta t)
```

或线性插值：

```text
risk(t_j) = (1-alpha) * risk[t_idx] + alpha * risk[t_idx + 1]
```

论文中建议说明采用哪种时间采样策略。若实现复杂度允许，线性插值更严谨；若先做工程闭环，`nearest` 或 `floor` 也可接受。

## 7. 单步风险增量

若使用 `hazard_rate`，单步坠机概率为：

```text
h_ij = hazard_rate_j * Delta t_ij
p_crash_ij = 1 - exp(-h_ij)
```

当前节点的存活概率为：

```text
P_surv_i = exp(-H_i)
```

于是三类风险增量为：

```text
Delta C_f = P_surv_i * p_crash_ij * e_fatality_j
Delta C_p = P_surv_i * p_crash_ij * e_property_j
Delta C_n = P_surv_i * r_noise_j * Delta t_ij
```

累计状态更新为：

```text
H_j = H_i + h_ij
C_f_j = C_f_i + Delta C_f
C_p_j = C_p_i + Delta C_p
C_n_j = C_n_i + Delta C_n
L_j = L_i + d_ij
```

这与论文第 3 章的状态演化逻辑一致：

- 致死风险和财产风险需要“存活到达 + 当前段坠机 + 坠机后果”。
- 噪声风险不需要坠机，但需要“存活到达 + 持续飞行时间”。

## 8. 综合目标函数

算法用于排序 open list 的综合代价建议采用：

```text
f(n) = g(n) + h(n)
```

其中 `g(n)` 是从起点到当前节点的真实累计综合代价，`h(n)` 是到终点的启发式估计。

单步综合代价为：

```text
Delta J =
  w_f * Delta C_f / Omega_f
+ w_p * Delta C_p / Omega_p
+ w_n * Delta C_n / Omega_n
+ w_d * d_ij / L_step_max
```

累计综合代价为：

```text
J_j = J_i + Delta J
```

其中：

```text
L_step_max = sqrt(3) * grid_resolution
```

`Omega_f`、`Omega_p`、`Omega_n` 是归一化分母，可由时空风险张量的理论或经验最大值给出。实现中必须加入极小值保护：

```text
Omega = max(Omega, eps)
```

## 9. 启发式函数

为保证算法表述严谨，推荐启发式函数优先使用距离下界：

```text
h(n) = w_d * ||p_n - p_goal|| / L_step_max
```

这个启发式不会高估剩余距离代价，比较稳妥。

不要轻易把未来风险估计放进 `h(n)` 并声称严格最优，因为未来风险随到达时间变化，难以保证启发式始终是 admissible。若后续使用 EDA、K-means 或风险走廊估计作为启发式，应表述为经验加速或近似搜索。

## 10. 未来点如何选择

未来点不是一次性预测完整路径，而是通过 A\* 的 open list 逐步选择。

每次扩展当前节点后，算法会生成最多 26 个候选邻居，并为每个候选邻居计算：

```text
f(candidate) = J_candidate + h(candidate)
```

然后把候选点加入 open list。下一步从 open list 中选择 `f` 最小的节点继续扩展：

```text
current = argmin_{n in open} f(n)
```

因此，未来点的选择由两部分共同决定：

1. 已经真实发生的累计代价 `J_candidate`
2. 到终点的估计剩余代价 `h(candidate)`

算法不会预先枚举全部未来时空路径，而是在搜索过程中不断展开最有希望的候选节点。

## 11. 算法伪代码

```text
Algorithm: Online Time-Sampled TD-RiskA*

Input:
  start, goal, t_departure
  dynamic risk tensors
  UAV speed v_uav
  constraints, weights

Initialize:
  H_start = 0
  P_surv_start = 1
  C_f_start = C_p_start = C_n_start = 0
  L_start = J_start = 0
  t_start = t_departure
  open = priority queue ordered by f = J + h
  push start into open

While open is not empty:
  current = pop node with minimum f

  If current.position == goal:
      return reconstructed path

  For each neighbor p_next in N_26(current.position):
      If p_next violates hard constraints:
          continue

      d = distance(current.position, p_next)
      dt = d / v_uav
      t_next = current.t + dt

      Sample dynamic risks at (p_next, t_next)

      h_step = hazard_rate(p_next, t_next) * dt
      p_crash = 1 - exp(-h_step)
      p_surv = exp(-current.H)

      delta_f = p_surv * p_crash * e_fatality(p_next, t_next)
      delta_p = p_surv * p_crash * e_property(p_next)
      delta_n = p_surv * r_noise(p_next, t_next) * dt

      H_next = current.H + h_step
      If H_next > -ln(P_threshold):
          continue

      L_next = current.L + d
      If L_next > L_max:
          continue

      delta_J = weighted_normalized_sum(delta_f, delta_p, delta_n, d)
      J_next = current.J + delta_J
      h_next = distance_heuristic(p_next, goal)
      f_next = J_next + h_next

      If p_next is not dominated by existing records:
          save father pointer
          push/update p_next in open

Output:
  risk-minimizing 3D route and cumulative risk records
```

## 12. 与完整 4D 搜索的区别

本文算法仍然利用四维风险信息：

```text
Risk(x,y,z,t)
```

但不把所有时间层都展开为搜索节点。区别如下：

| 方法                 | 搜索节点                 | 风险使用方式               | 计算特征             |
| -------------------- | ------------------------ | -------------------------- | -------------------- |
| 完整 4D A\*          | `(x,y,z,t)`              | 枚举所有时间层             | 精确但易维度爆炸     |
| 出发时刻切片 RiskA\* | `(x,y,z)`                | 全路径使用`Q(t_departure)` | 快，但时间依赖较弱   |
| 本文推荐 TD-RiskA\*  | `(x,y,z)` + 到达时间状态 | 每步按`t_i` 在线采样       | 兼顾动态性与可计算性 |

因此，本文推荐方法比静态时间切片更能体现飞行过程中的动态风险变化，同时比完整四维展开更适合城市尺度实验。

## 13. 论文中可采用的表述

可在算法章节中使用如下表述：

> 为避免显式构建完整四维时空图导致的维度爆炸，本文将时间维作为搜索状态中的到达时间标签，而非独立展开的图维度。在给定出发时刻后，算法在三维栅格空间中执行 26 邻域 A\* 搜索；每当扩展候选节点时，根据当前路径累计飞行时间计算候选节点的实际到达时刻，并从动态风险张量中在线采样该时刻的坠机危险率、人口暴露、车辆暴露、财产损失和噪声影响。由此得到的单步风险增量被累积到路径代价中，从而实现时间依赖风险感知的三维航路规划。

## 14. 适用边界

该算法适用于：

- 给定 OD 对和出发时间的单次航路规划。
- 风险场随时间变化，但变化速度不至于要求连续时间最优控制。
- 栅格分辨率适中，且可通过约束、启发式和走廊筛选降低搜索空间。

如果飞行时间很短，且风险变化慢，也可以退化为出发时刻切片近似：

```text
Risk(x,y,z,t_i) ≈ Risk(x,y,z,t_departure)
```

但论文中应明确这是一种准静态近似，而不是完整的时间依赖搜索。

## 15. 后续实现优先级

建议代码实现按以下顺序推进：

1. 先实现三维 26 邻域 TD-RiskA\*，每步按到达时间采样风险。
2. 输出每一步的 `t_i`、`p_crash`、`delta_fatality`、`delta_property`、`delta_noise`、`J_i`。
3. 加入生存阈值、最大航程、障碍、高度范围等硬约束。
4. 做小规模合成实验，证明时间依赖风险会改变路径。
5. 再引入分层走廊或并行 OD 计算，支撑城市尺度案例。

# 补充说明

是的，你的这个伪代码框架在核心的**物理计算**和**逻辑链条**上是完全正确的！你非常完美地将我们在 LaTeX 建模中讨论的马尔可夫演化、条件概率折减以及无量纲化处理，全部翻译成了算法逻辑。

作为你的导师，我仔细审视了你的这份伪代码，有几个设计得极其漂亮、展现了深厚功底的闪光点，但同时，也有一个**极易在实际写代码时写出 Bug 的“多标签（Label-Setting）”逻辑漏洞**需要向你指出。

我们先看闪光点，再来堵死这个逻辑漏洞。

---

### 一、 两个处理得极其漂亮的“学术闪光点”

#### 1. 累积危险率 $H$（Cumulative Hazard Rate）的引入

你在代码里使用了 `H_next = current.H + h_step`，并通过 `p_surv = exp(-current.H)` 来反推存活概率。
**这在数值计算上是一个非常高级且聪明的做法。**
因为概率相乘（例如 $0.99 \times 0.98 \times \dots$）在长距离路径规划中很容易发生**数值下溢（Numerical Underflow）**，导致计算机最后将其舍入为 0。而你将乘法转化为了对数空间（Log-space）下的加法：$H = \sum h_{\mathrm{step}}$，不仅保证了数值计算的极高稳定性，而且在判断安全熔断时：
`If H_next > -ln(P_threshold): continue`
这个不等式与 $P_{\mathrm{surv}} < P_{th}$ 是数学上完全等价的，计算速度还更快！

#### 2. 条件风险期望增量（$\Delta f, \Delta p, \Delta n$）的精确兑现

你的这三行计算：

```python
delta_f = p_surv * p_crash * e_fatality(...)
delta_p = p_surv * p_crash * e_property(...)
delta_n = p_surv * r_noise(...) * dt
```

精准地表达了我们在 LaTeX 里的数学物理定义：

- 碰撞损失（致死、财产）是**双重条件概率**：必须存活到达（$P_{\mathrm{surv}}$）且在当前步坠毁（$P_{\mathrm{crash}}$）才会发生；
- 噪音是**持续累积暴露**：只要存活到达，哪怕不坠机，也会随着驻留时间 $dt$ 持续累积。
  这说明你彻底吃透了这两章的物理机制。

---

### 二、 一个必须引起高度重视的“多标签算法陷阱”

你的伪代码在最后几行写道：

```python
If p_next is not dominated by existing records:
    save father pointer
    push/update p_next in open
```

**注意！如果你在写代码时，把 `open` 表和“记录”直接绑定在物理网格 `p_next` 上，你的算法就会彻底退化并产生 Bug！**

#### 为什么？

因为我们刚刚讨论过，这是一个**非马尔可夫问题**。同一个物理网格 $\mathbf{p} = (x,y,z)$，在不同的时间 $t$、以不同的存活率 $P_{\mathrm{surv}}$ 到达时，会产生多个**互不支配的帕累托最优状态（标签）**。

- **传统 A\*（Node-Setting）**：一个网格在 `open` 表里最多只能保留一个状态。如果新路代价更低，就**更新（overwrite）**它。
- **多标签 A\*（Label-Setting）**：同一个网格 $\mathbf{p}$，在 `open` 表里可以**同时并存多个不同的标签**！
    - 例如，标签 1（飞得快但存活率低）和标签 2（飞得慢但存活率高）都到达了同一个网格 $\mathbf{p}$。
    - 因为它们互不支配，你必须**同时把标签 1 和标签 2 压入 `open` 队列**。你不能用其中一个去 `update`（覆盖）另一个。

#### 正确的算法实现逻辑：

因此，你的队列 `open` 存储的元素不应该是“网格 $p$”，而应该是**“标签 $L$”**。

我建议你将伪代码的最后几行，修改为如下严密的**多标签更新机制**：

```python
      # 1. 构造新的候选标签 (保存父指针以回溯)
      L_cand = Label(position=p_next, t=t_next, H=H_next, J=J_next, f=f_next, father=current_Label)

      # 2. 检查 p_next 节点上已有的非支配标签集合 L_set(p_next)
      # 如果候选标签被该节点已有的任何一个旧标签支配，直接抛弃
      If L_cand is dominated by any L_old in L_set(p_next):
          continue

      # 3. 如果候选标签没有被支配，说明它是一个新的帕累托最优状态：
      # a) 清退该节点上所有被新标签 L_cand 支配的旧标签
      For each L_old in L_set(p_next):
          If L_cand dominates L_old:
              L_set(p_next).remove(L_old)
              open.remove(L_old) # 如果旧标签还在 open 队列中，也将其移除

      # b) 将新标签存入节点集合，并压入优先队列
      L_set(p_next).add(L_cand)
      open.push(L_cand)
```

---

### 三、 导师总结

你的思路完全走在正确的轨道上。只要把最后这一处关于**“多标签（Label-Setting）而非常规网格更新（Node-Setting）”**的逻辑细节改精准，你的 TD-RiskA\* 算法在学术推导和代码落地上就都毫无破绽了。

你现在对这个算法的在线时间采样（Online Time-Sampled）和多维标签演化，是不是已经有绝对的信心了？改完这一步，我们的系统建模和第一阶段算法就彻底大功告成了！
