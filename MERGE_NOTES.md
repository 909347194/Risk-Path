# 项目合并说明文档

## 📋 合并概览

本次合并将两个独立的无人机路径规划项目整合到统一的 `Risk-Path` 项目中。

### 源项目

1. **EDA-A-star** (`src/EDA-A-star`)
   - 基于估计分布算法（EDA）和成本感知 A* 的路径规划系统
   - 实现了 Two-Stage EDA-CostA* 算法
   - 包含完整的实验框架和测试套件

2. **Risk-based_Air_Path_Planning** (`src/Risk-based_Air_Path_Planning`)
   - 基于多维度风险评估的空中走廊设计系统
   - 包含 Air_Corridor_Design 核心模块
   - 提供多种路径规划算法（A*, Dijkstra, Greedy）

---

## 🔄 合并操作记录

### 1. 目录结构调整

#### EDA-A-star 迁移
```
原路径: src/EDA-A-star/
新路径: src/eda_astar/
操作:   直接重命名
```

**保留内容**:
- ✅ `core/` - 核心算法模块
- ✅ `experiments/` - 实验脚本
- ✅ `utils/` - 工具模块
- ✅ `data/` - 数据文件
- ✅ `docs/` - 技术文档
- ✅ `tests/` - 单元测试
- ✅ 所有配置文件和文档

#### Air Corridor Design 提取
```
原路径: src/Risk-based_Air_Path_Planning/Air_Corridor_Design/
新路径: src/air_corridor/
操作:   移动核心代码模块
```

**保留内容**:
- ✅ `Data_Process/` - 数据处理模块
- ✅ `Key_Elements/` - 关键要素定义
- ✅ `Optimization/` - 优化算法
- ✅ `Plot/` - 可视化模块
- ✅ 所有主程序入口文件 (`main*.py`)

**未迁移内容** (保留在原位置供参考):
- ⚠️ `src/Risk-based_Air_Path_Planning/` - 原始项目根目录（含 README、配置文件等）
- ⚠️ `Experiments/`, `Scripts/`, `Notebooks/` 等辅助目录

---

### 2. 依赖合并

#### 合并策略
将两个项目的依赖整合到根目录的 `pyproject.toml` 中。

#### 主要依赖类别

| 类别 | 包名 | 用途 |
|------|------|------|
| **科学计算** | numpy, pandas, scipy | 数值计算和数据处理 |
| **地理空间** | geopandas, shapely, rasterio, pyproj | GIS 数据处理 |
| **地图投影** | cartopy, cnmaps | 地图可视化和中国地图支持 |
| **可视化** | matplotlib, plottable, pydeck | 2D/3D 图形绘制 |
| **机器学习** | scikit-learn, joblib | 聚类和优化算法 |
| **统计分析** | statsmodels | 统计建模 |
| **网络请求** | urllib3, beautifulsoup4 | 数据获取 |
| **Jupyter** | notebook, nbclient | Notebook 支持 |

---

### 3. 统一入口点

创建了新的 `main.py` 作为统一入口，提供交互式菜单：

```bash
python main.py
```

**功能**:
- [1] EDA-CostA* 实验运行
  - 1.1 Standard Cost A*
  - 1.2 Original EDA-A*
  - 1.3 Two-Stage EDA-CostA*
  - 1.4 算法对比
- [2] Air Corridor Design 任务
  - 2.1 主程序
  - 2.2 算法性能测试
  - 2.3 地图预处理
  - 2.4 敏感性分析（风险权重）
  - 2.5 敏感性分析（权衡权重）

---

## 📂 最终项目结构

```
Risk-Path/
│
├── src/
│   ├── eda_astar/                    # EDA-CostA* 系统
│   │   ├── core/                     # 核心算法
│   │   │   ├── path_planning/       # 路径规划
│   │   │   └── risk_model/          # 风险模型
│   │   ├── experiments/             # 实验脚本 (4个)
│   │   ├── utils/                   # 工具模块
│   │   ├── data/                    # 数据文件
│   │   ├── tests/                   # 单元测试
│   │   ├── docs/                    # 技术文档
│   │   └── config.py                # 配置文件
│   │
│   └── air_corridor/                # 空中走廊设计系统
│       ├── Data_Process/            # 数据处理
│       ├── Key_Elements/            # 关键要素
│       ├── Optimization/            # 优化算法
│       ├── Plot/                    # 可视化
│       ├── main.py                  # 主入口
│       ├── main_algorithm_performance.py
│       ├── main_preparemap.py
│       ├── main_sensitivity_riskweight.py
│       └── main_sensitivity_tradeoffweight.py
│
├── data/                            # 共享数据目录（待整理）
├── pyproject.toml                   # 统一依赖配置
├── main.py                          # 统一入口脚本
├── README.md                        # 项目总览
└── MERGE_NOTES.md                   # 本文件
```

---

## ✅ 验证清单

### 已完成
- [x] EDA-A-star 重命名为 eda_astar
- [x] Air_Corridor_Design 移动到 air_corridor
- [x] 依赖合并到 pyproject.toml
- [x] 创建综合 README.md
- [x] 创建统一入口 main.py
- [x] 语法检查通过

### 待完成
- [ ] 安装依赖并测试运行
- [ ] 整理 data 目录结构
- [ ] 更新导入路径（如有必要）
- [ ] 运行单元测试
- [ ] 删除或归档原始 Risk-based_Air_Path_Planning 目录

---

## 🔧 后续步骤建议

### 1. 依赖安装测试
```bash
uv sync
```

### 2. 运行基本测试
```bash
# 测试 EDA-Astar
cd src/eda_astar
python experiments/experiment_01_standard_astar.py

# 测试 Air Corridor
cd src/air_corridor
python main.py
```

### 3. 数据目录整理
建议将两个项目的数据文件统一到 `data/` 目录：
```
data/
├── eda_astar/
│   ├── buildings/
│   ├── population/
│   └── road/
└── air_corridor/
    ├── Building/
    └── Travel/
```

### 4. 导入路径更新
检查并更新以下可能的导入问题：
- `from Air_Corridor_Design.XXX` → `from air_corridor.XXX`
- 相对导入路径调整

### 5. 清理旧目录
确认一切正常后，可以：
```bash
# 备份后删除
mv src/Risk-based_Air_Path_Planning backup/Risk-based_Air_Path_Planning
```

---

## 📝 注意事项

### 导入兼容性
两个项目使用了不同的导入风格：
- **eda_astar**: 使用绝对导入和包结构
- **air_corridor**: 使用相对导入

可能需要调整部分导入语句以确保兼容性。

### 配置冲突
- `eda_astar/config.py` 使用 Path 对象
- `air_corridor` 使用字符串路径

建议统一为 Path 对象以提高可维护性。

### Python 版本要求
- eda_astar: Python 3.12+
- air_corridor: Python 3.9+
- **合并后**: Python 3.9+ (满足最低要求)

---

## 🎯 预期收益

1. **统一管理**: 两个相关项目在同一个仓库中
2. **代码复用**: 可以共享风险模型、数据处理等模块
3. **对比实验**: 方便进行算法性能对比
4. **文档集中**: 所有文档在一个地方
5. **依赖简化**: 统一的依赖管理

---

**合并日期**: 2026-05-11  
**执行者**: Lingma Assistant
