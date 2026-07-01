### 结论：是否应该做类似的工作？

对于 methods/spatiotemporal_heterogeneity 模块，我的建议是： “吸收其灵魂（状态向量），抛弃其外壳（重量级点类）” 。
建议 1：引入状态向量 (State Vector) —— 应该做
在进入路径规划阶段（算法层）时， 必须 设计状态向量。

- 原因 : 风险路径规划（Risk-aware Planning）不同于简单的最短路径。风险、噪音和存活概率在路径上是 累积或非线性变化 的。
- 4D 扩展 : 状态向量需要包含时间维度 T 。例如，当无人机从 (x1, y1, z1) 飞到 (x2, y2, z2) ，不仅坐标变了，时间 t 也在增加，对应的风险场也会随之变化。 建议 2：不推荐使用 Point 类表示整个网格 —— 不应该做
- 原因 : spatiotemporal_heterogeneity 的网格规模通常很大（如 100x100x12x96 = 1152万个单元）。如果每个单元都实例化一个 Point 对象，内存会溢出。
- 替代方案 : 继续使用现有的 GridSystem 和张量场。仅在 A* 搜索算法运行过程中，为 Open List 中的“探索中节点”创建轻量级的状态对象或结构体。

### 3. 改进建议 (Todo List)

如果你准备在 spatiotemporal_heterogeneity 中实现类似的规划逻辑，可以参考以下结构：

- 设计轻量级 Node : 仅用于搜索算法，不存储静态地图信息。
  ```
  class SearchNode:
      def __init__(self, x, y, z, t, 
  state_vector):
          self.coords = (x, y, z, t)
          self.state = state_vector  # [CumDis, 
  CumRisk, CumNoise, P_survival]
          self.parent = None
  ```
- 利用张量场 : 在搜索时，直接通过 Cost_total[x, y, z, t] 索引风险值，而不是去点对象里找。
- 动态更新 : 状态向量中的 P_survival （存活概率）应按 P_safe_new = P_safe_old * (1 - P_crash[x,y,z,t]) 进行乘法累积。
  这种做法既保留了 air_corridor 在风险建模上的科学性（状态向量），又发挥了 spatiotemporal_heterogeneity 在大数据量下的性能优势。
