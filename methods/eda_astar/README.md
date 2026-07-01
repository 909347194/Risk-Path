# EDA-CostA* UAV Path Planning System

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 简介

基于**估计分布算法（EDA）**和**成本感知A\***的无人机城市环境路径规划系统。实现了Pang et al. (2022)论文中的Two-Stage EDA-CostA*算法，集成多维度风险评估模型。

### 核心特性

✅ **Three Algorithms**: Standard Cost A*, Original EDA-A*, Two-Stage EDA-CostA*  
✅ **Risk Integration**: Fatality + Property + Noise + Traffic risks  
✅ **Advanced Heuristics**: Adaptive global/local guidance (Eq. 24-26)  
✅ **Professional Visualization**: Publication-quality 3D plots  

---

## 📁 项目结构

```
EDAcostAstar/
│
├── core/                    # 🎯 核心算法实现
│   ├── path_planning/      # 路径规划算法
│   └── risk_model/         # 风险模型
│
├── experiments/            # 🧪 实验脚本
│   ├── experiment_01_standard_astar.py
│   ├── experiment_02_original_eda.py
│   ├── experiment_03_two_stage_eda.py
│   └── experiment_04_comparison.py
│
├── output/                 # 📊 实验结果和可视化输出
│
├── tests/                  # 🧪 单元测试
│
├── utils/                  # 🔧 工具模块
│   └── visualizer.py       # 可视化工具
│
├── data/                   # 📂 数据文件
│   ├── buildings/
│   ├── population/
│   └── road/
│
└── docs/                   # 📚 技术文档
    ├── ALGORITHMS.md
    ├── FORMULAS.md
    ├── API_REFERENCE.md
    └── VALIDATION_REPORT.md
```

---

## 🚀 快速开始

### 安装依赖

```bash
uv sync
```

### 运行实验

```bash
# 实验1: Standard Cost A*
uv run python experiments/experiment_01_standard_astar.py

# 实验2: Original EDA-A*
uv run python experiments/experiment_02_original_eda.py

# 实验3: Two-Stage EDA-CostA* (主要贡献)
uv run python experiments/experiment_03_two_stage_eda.py

# 实验4: 算法对比
uv run python experiments/experiment_04_comparison.py
```

### 查看结果

所有实验结果保存在 `output/` 目录：
- `output/experiment_01/` - Standard A* 结果
- `output/experiment_02/` - Original EDA 结果
- `output/experiment_03/` - Two-Stage EDA 结果
- `output/experiment_04_comparison/` - 对比结果

---

## 💻 基础使用

```python
from core import Grid3D, IntegratedCostModel, TwoStageEDACostAStarSearcher

# 1. 创建3D网格
grid = Grid3D(bounds=bounds, cell_size=80.0, layers=[30, 60, 90, 120])

# 2. 计算风险成本
cost_model = IntegratedCostModel(grid, population_raster, buildings)
cost_map = cost_model.compute_layer_costs()

# 3. 构建路径图
from core.path_planning import Grid3DPathGraph
graph = Grid3DPathGraph(grid, cost_map, clearance=5.0)
graph.build_graph()

# 4. 路径规划
planner = TwoStageEDACostAStarSearcher(graph, cost_map)
path, cost, metrics = planner.search(start, goal)
```

---

## 📚 文档

- **[experiments/README.md](experiments/README.md)** - 实验详细说明
- **[docs/ALGORITHMS.md](docs/ALGORITHMS.md)** - 算法完整说明
- **[docs/FORMULAS.md](docs/FORMULAS.md)** - 公式实现对照表
- **[docs/API_REFERENCE.md](docs/API_REFERENCE.md)** - API参考手册
- **[docs/VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md)** - 验证报告

---

## 🎯 预期结果

| 算法 | 成本 | 航点数 | 时间 |
|------|------|--------|------|
| Standard Cost A* | ~98.17 | ~73 | ~2s |
| Original EDA-A* | ~99.00 | ~75 | ~15s |
| Two-Stage EDA-CostA* | ~98.17 | ~73 | ~20s |

**关键发现**: Two-Stage EDA在保持最优解精度的同时，通过预筛选显著缩小搜索空间。

---

## 📄 许可证

MIT License

---

**最后更新**: 2026-04-27