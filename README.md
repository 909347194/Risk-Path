# Risk-Path: UAV Path Planning & Air Corridor Design System

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📖 项目简介

Risk-Path 是一个综合性的无人机路径规划与空中走廊设计系统，集成了两种先进的路径规划算法：

1. **EDA-CostA***: 基于估计分布算法（EDA）和成本感知 A* 的两阶段路径规划
2. **Air Corridor Design**: 基于多维度风险评估的空中走廊优化设计

### 核心特性

✅ **多种算法支持**: Standard Cost A*, Original EDA-A*, Two-Stage EDA-CostA*, Dijkstra, Greedy Best-First
✅ **综合风险评估**: 死亡风险 + 财产损失 + 噪声污染 + 交通密度
✅ **高级启发式策略**: 自适应全局/局部引导
✅ **专业可视化**: 出版级质量的 3D 体素图、路径图、热力图
✅ **敏感性分析**: 多权重组合的路径对比分析

---

```plaintext
├── 📁 data/                        # [不要提交到 Git] 数据存放区
│   ├── 📁 01_raw/                  # 原始数据 (OSM .pbf, WorldPop .tif, 天气 .csv等)
│   ├── 📁 02_processed/            # 对齐后(50m分辨率)的中间空间数据 (.shp, .geojson)
│   └── 📁 03_tensors/              # 张量引擎的最终产物 (极其重要：存放预计算的 .npy 或 .h5 文件)
│
├── 📁 configs/                     # 配置管理层 (参数与权重控制中心)
│   ├── env_config.yaml             # 环境配置：网格大小(50x50x10)、城市边界经纬度、时间步长等
│   ├── risk_params.yaml            # 风险参数：基准失效率、建筑敏感系数、高度阈值等
│   └── weight_scenarios.yaml       # 多目标权重配置：(如 急救模式 w1-w4, 普通物流模式 w1-w4)
│
├── 📁 src/                         # 核心代码源目录 (按照我们设计的四层架构严格解耦)
│   │
│   ├── 📁 data_provision/          # 【架构第1层】数据供给层 (预处理)
│   │   ├── __init__.py
│   │   ├── osm_parser.py           # 解析 OSM 提取建筑高度、道路网络、土地利用类型 (Landuse)
│   │   ├── pop_resampler.py        # WorldPop 人口栅格的降采样与对齐
│   │   └── weather_interpolator.py # 气象数据(风/雨)的时空插值处理
│   │
│   ├── 📁 tensor_engine/           # 【架构第2层】张量引擎层 (核心大动脉，生成预计算张量)
│   │   ├── __init__.py
│   │   ├── static_obstacle.py      # 生成 3D 静态建筑遮挡布尔张量
│   │   ├── dynamic_pcrash.py       # 生成 4D P_crash 概率场张量 (结合风、雨、城市峡谷)
│   │   ├── dynamic_population.py   # 生成 3D 潮汐人口密度张量 (基于POI激活函数)
│   │   ├── dynamic_noise.py        # 生成 4D 噪音社会成本张量 (包含 S-T 查表逻辑)
│   │   └── tensor_builder.py       # 组装/归一化各项成本，输出最终的 Cost_Total Tensor
│   │
│   ├── 📁 algorithms/              # 【架构第3层】算法管线层 (单向流水线)
│   │   ├── __init__.py
│   │   ├── eda_macro.py            # EDA 全局宏观寻路：生成 B-Spline 控制点/航路点及无A*适应度评估
│   │   ├── kmeans_corridor.py      # K-means 聚类提取：基于 EDA 优秀种群生成 3D 掩码走廊 (Mask)
│   │   ├── cost_astar.py           # TD-CostA* 精确寻路：带时间推进的 O(1) 查表与剪枝搜索
│   │   └── pipeline_runner.py      # 流水线编排器：串联 EDA -> Kmeans -> CostA* 
│   │
│   └── 📁 eval_and_vis/            # 【架构第4层】评估与可视化层
│       ├── __init__.py
│       ├── metrics.py              # 计算各条路径的真实运营成本、伤亡期望、噪音总和
│       ├── pareto_front.py         # 计算并绘制多目标帕累托前沿
│       └── plot_4d_trajectory.py   # 3D 城市渲染与轨迹绘制 (建议基于 Plotly 或 PyVista)
│
├── 📁 scripts/                     # 脚本目录 (直接运行的入口文件，供服务器跑实验用)
│   ├── 01_build_tensors.py         # 独立运行：读取 data/01_raw，运行 tensor_engine，生成 .npy
│   ├── 02_run_experiments.py       # 独立运行：加载张量，读取 configs 里的不同权重，批量跑算法
│   └── 03_generate_plots.py        # 独立运行：读取跑完的轨迹 log，生成论文插图
│
├── 📁 tests/                       # 单元测试 (科学严谨性的保障)
│   ├── test_tensors.py             # 检查张量是否出现 NaN，概率是否 > 1
│   └── test_astar_heuristics.py    # 测试 A* 的启发式函数是否单调
│
├── .gitignore                      # 忽略大文件、缓存文件 (极其重要)
├── requirements.txt                # 依赖包列表 (numpy, scipy, geopandas, networkx, plotly等)
└── README.md                       # 项目说明 (记录如何复现你的实验)
```

## 📁 项目结构

```
Risk-Path/
│
├── src/
│   ├── eda_astar/                    # EDA-CostA* 路径规划系统
│   │   ├── core/                     # 核心算法模块
│   │   │   ├── path_planning/       # 路径规划算法实现
│   │   │   └── risk_model/          # 风险模型计算
│   │   ├── experiments/             # 实验脚本
│   │   ├── utils/                   # 工具模块
│   │   ├── data/                    # 数据文件
│   │   └── docs/                    # 技术文档
│   │
│   └── air_corridor/                # 空中走廊设计系统
│       ├── Data_Process/            # 数据处理模块
│       ├── Key_Elements/            # 关键要素定义
│       ├── Optimization/            # 优化算法
│       ├── Plot/                    # 可视化模块
│       └── main*.py                 # 主程序入口
│
├── data/                            # 共享数据目录
├── pyproject.toml                   # 项目配置与依赖
└── README.md                        # 项目说明
```

---

## 🚀 快速开始

### 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 运行 EDA-CostA* 实验

```bash
cd src/eda_astar

# 实验1: Standard Cost A*
uv run python experiments/experiment_01_standard_astar.py

# 实验2: Original EDA-A*
uv run python experiments/experiment_02_original_eda.py

# 实验3: Two-Stage EDA-CostA* (主要贡献)
uv run python experiments/experiment_03_two_stage_eda.py

# 实验4: 算法对比
uv run python experiments/experiment_04_comparison.py
```

### 运行 Air Corridor Design

```bash
cd src/air_corridor

# 单次路径规划
uv run python main.py

# 算法性能对比
uv run python main_algorithm_performance.py

# 地图预处理
uv run python main_preparemap.py

# 敏感性分析
uv run python main_sensitivity_riskweight.py
uv run python main_sensitivity_tradeoffweight.py
```

---

## 💻 基础使用示例

### EDA-CostA* 路径规划

```python
from src.eda_astar.core import Grid3D, IntegratedCostModel, TwoStageEDACostAStarSearcher

# 1. 创建3D网格
grid = Grid3D(bounds=bounds, cell_size=80.0, layers=[30, 60, 90, 120])

# 2. 计算风险成本
cost_model = IntegratedCostModel(grid, population_raster, buildings)
cost_map = cost_model.compute_layer_costs()

# 3. 构建路径图
from src.eda_astar.core.path_planning import Grid3DPathGraph
graph = Grid3DPathGraph(grid, cost_map, clearance=5.0)
graph.build_graph()

# 4. 路径规划
planner = TwoStageEDACostAStarSearcher(graph, cost_map)
path, cost, metrics = planner.search(start, goal)
```

### Air Corridor Design

```python
from src.air_corridor.Optimization.main_procedure import main_procedure

# 配置参数
params = {
    'city': 'Beijing',
    'Fatality_weight': 0.7,
    'Property_weight': 0.2,
    'Noise_weight': 0.1,
    'Trade-off weight_distance': 0.1,
    # ... 更多参数
}

# 执行路径规划
main_procedure(params)
```

---

## 📊 预期结果

### EDA-CostA* 算法性能对比


| 算法                 | 成本   | 航点数 | 时间 |
| -------------------- | ------ | ------ | ---- |
| Standard Cost A*     | ~98.17 | ~73    | ~2s  |
| Original EDA-A*      | ~99.00 | ~75    | ~15s |
| Two-Stage EDA-CostA* | ~98.17 | ~73    | ~20s |

**关键发现**: Two-Stage EDA 在保持最优解精度的同时，通过预筛选显著缩小搜索空间。

---

## 📚 详细文档

### EDA-CostA* 文档

- **[src/eda_astar/docs/ALGORITHMS.md](src/eda_astar/docs/ALGORITHMS.md)** - 算法完整说明
- **[src/eda_astar/docs/FORMULAS.md](src/eda_astar/docs/FORMULAS.md)** - 公式实现对照表
- **[src/eda_astar/docs/API_REFERENCE.md](src/eda_astar/docs/API_REFERENCE.md)** - API参考手册
- **[src/eda_astar/experiments/README.md](src/eda_astar/experiments/README.md)** - 实验详细说明

### Air Corridor Design 文档

- **[src/air_corridor/MIGRATION.md](src/Risk-based_Air_Path_Planning/MIGRATION.md)** - 迁移指南
- **[src/air_corridor/QUICKSTART.md](src/Risk-based_Air_Path_Planning/QUICKSTART.md)** - 快速入门

---

## 🔧 开发指南

### 添加新依赖

```bash
uv add <package-name>
```

### 运行测试

```bash
# EDA-Astar 测试
cd src/eda_astar
uv run python -m pytest tests/

# Air Corridor 测试
cd src/air_corridor
uv run python -m pytest Tests/
```

---

## 📄 许可证

MIT License

---

## 👥 贡献者

- Kai Zhou (zhouk23@mails.tsinghua.edu.cn)
- 欢迎提交 Issue 和 Pull Request！

---

**最后更新**: 2026-05-11
