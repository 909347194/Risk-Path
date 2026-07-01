# 三维可视化指南

**创建时间**: 2026-04-27  
**状态**: ✅ **已实现 - Matplotlib + Plotly双引擎**

---

## 🎯 概述

项目提供**两套三维可视化方案**，满足不同需求：

| 特性 | Matplotlib (静态) | Plotly (交互式) |
|------|------------------|----------------|
| **输出格式** | PNG图片 | HTML文件 |
| **交互性** | ❌ 静态 | ✅ 旋转、缩放、平移 |
| **文件大小** | 小 (KB-MB) | 较大 (MB) |
| **分享便捷** | ✅ 直接嵌入 | 需浏览器打开 |
| **适用场景** | 论文、报告 | 演示、协作 |
| **依赖** | matplotlib, seaborn | plotly |

---

## 📦 安装依赖

### Matplotlib（已安装）
```bash
uv sync  # 自动安装pyproject.toml中的依赖
```

### Plotly（可选，用于交互式可视化）
```bash
uv add plotly
```

---

## 🚀 快速开始

### 方案1: Matplotlib静态可视化（默认）

实验脚本会自动生成静态PNG图片：

```bash
cd src/EDAcostAstar
uv run python experiments/experiment_01_standard_astar.py
```

**输出示例**:
```
output/experiment_01/
├── path_3d.png              # 3D路径图
├── cost_map_slices.png      # 成本图切片
└── results.json             # 结果数据
```

---

### 方案2: Plotly交互式可视化（推荐）⭐

#### A. 在实验中自动启用

实验脚本会检测Plotly是否安装，如果存在则自动生成HTML文件：

```bash
# 确保已安装plotly
uv add plotly

# 运行实验
uv run python experiments/experiment_01_standard_astar.py
```

**输出示例**:
```
output/experiment_01/
├── path_3d.png                      # 静态图（Matplotlib）
├── path_3d_interactive.html         # 交互图（Plotly）✨
└── results.json
```

**使用方法**:
1. 在文件管理器中双击 `.html` 文件
2. 或在浏览器中打开
3. 可以**旋转、缩放、平移**3D视图！

---

#### B. 使用演示脚本学习

```bash
cd src/EDAcostAstar
uv run python examples/demo_interactive_visualization.py
```

这会创建5个演示：
1. ✅ 基础3D路径
2. ✅ 多算法对比
3. ✅ 成本图体积渲染
4. ✅ EDA收敛历史
5. ✅ 完整仪表板

所有HTML文件保存在 `output/demo/` 目录。

---

## 💻 API使用示例

### 1. 基础3D路径可视化

```python
from utils.interactive_visualizer import InteractiveVisualizer

# 创建可视化工具
viz = InteractiveVisualizer(output_dir="output/my_experiment")

# 准备路径数据
path = [
    (0, 0, 0),      # (layer, row, col)
    (1, 10, 10),
    (2, 20, 20),
    (3, 30, 30),
]

# 创建交互式图表
fig = viz.plot_path_3d_interactive(
    path=path,
    title="My 3D Path",
    show_cost_map=False  # 可选：显示成本图背景
)

# 保存为HTML
viz.save_figure(fig, "my_path.html")

# 或在浏览器中打开
fig.show()
```

---

### 2. 多算法对比

```python
from utils.interactive_visualizer import InteractiveVisualizer

viz = InteractiveVisualizer(output_dir="output/comparison")

# 准备多个路径
paths_dict = {
    'Standard A*': path1,
    'Original EDA-A*': path2,
    'Two-Stage EDA': path3,
}

# 创建对比图
fig = viz.plot_multiple_paths_interactive(
    paths_dict=paths_dict,
    title="Algorithm Comparison",
    colors=['blue', 'red', 'green']  # 自定义颜色
)

viz.save_figure(fig, "comparison.html")
```

---

### 3. 成本图体积渲染

```python
import numpy as np
from utils.interactive_visualizer import InteractiveVisualizer

viz = InteractiveVisualizer(output_dir="output/cost_map")

# 3D成本图 (layers, rows, cols)
cost_map = np.random.rand(4, 50, 50) * 10

# 创建体积图
fig = viz.plot_cost_map_3d_interactive(
    cost_map=cost_map,
    title="Cost Map Volume",
    colorscale='Viridis'  # 可选: 'Hot', 'Plasma', 'Inferno'等
)

viz.save_figure(fig, "cost_volume.html")
```

---

### 4. EDA收敛历史

```python
from utils.interactive_visualizer import InteractiveVisualizer

viz = InteractiveVisualizer(output_dir="output/eda")

# 收敛数据
convergence_history = [
    {'generation': 0, 'best_fitness': 100, 'avg_fitness': 150},
    {'generation': 1, 'best_fitness': 95, 'avg_fitness': 140},
    # ... 更多代
]

# 创建收敛图
fig = viz.plot_eda_convergence_interactive(
    convergence_history=convergence_history,
    title="EDA Convergence"
)

viz.save_figure(fig, "convergence.html")
```

---

### 5. 完整仪表板

```python
from utils.interactive_visualizer import InteractiveVisualizer

viz = InteractiveVisualizer(output_dir="output/dashboard")

# 创建包含多个子图的仪表板
fig = viz.create_dashboard(
    path=path,
    cost_map=cost_map,
    convergence_history=convergence_history,
    title="Complete Experiment Dashboard"
)

viz.save_figure(fig, "dashboard.html")
```

---

## 🎨 自定义选项

### 主题设置

```python
# 支持的主题
themes = [
    'plotly_white',      # 白色背景（默认）
    'plotly_dark',       # 深色背景
    'ggplot2',           # R风格
    'seaborn',           # Seaborn风格
    'simple_white',      # 简洁白色
]

viz = InteractiveVisualizer(theme='plotly_dark')
```

### 颜色和样式

```python
# 3D路径自定义
fig = viz.plot_path_3d_interactive(
    path=path,
    opacity=0.8,              # 透明度
    show_cost_map=True,       # 显示成本图背景
    colorscale='Hot'          # 成本图颜色
)
```

---

## 📊 实验脚本集成

所有实验脚本已自动集成交互式可视化：

### experiment_01 (Standard A*)
```bash
uv run python experiments/experiment_01_standard_astar.py
```
**输出**: `output/experiment_01/path_3d_interactive.html`

### experiment_02 (Original EDA-A*)
```bash
uv run python experiments/experiment_02_original_eda.py
```
**输出**: `output/experiment_02/path_3d_interactive.html`

### experiment_03 (Two-Stage EDA)
```bash
uv run python experiments/experiment_03_two_stage_eda.py
```
**输出**: `output/experiment_03/path_3d_interactive.html`

### experiment_04 (Comparison)
```bash
uv run python experiments/experiment_04_comparison.py
```
**输出**: `output/experiment_04_comparison/comparison_3d_interactive.html`

---

## 🔧 故障排除

### Q1: "ModuleNotFoundError: No module named 'plotly'"

**解决**:
```bash
uv add plotly
```

### Q2: HTML文件无法打开

**原因**: 某些旧版浏览器不支持嵌入式JavaScript

**解决**:
- 使用现代浏览器：Chrome, Firefox, Edge, Safari
- 或使用Python内置服务器：
  ```bash
  cd output/experiment_01
  python -m http.server 8000
  # 访问 http://localhost:8000/path_3d_interactive.html
  ```

### Q3: 3D渲染缓慢

**原因**: 数据点过多

**解决**:
```python
# 降采样路径
path_sampled = path[::5]  # 每5个点取1个

# 或降低成本图分辨率
cost_map_downsampled = cost_map[::2, ::2, ::2]
```

### Q4: 想要同时保存静态和交互图

**解决**: 实验脚本已自动保存两种格式！
- `.png` - 用于论文/报告
- `.html` - 用于演示/协作

---

## 📝 最佳实践

### 1. 论文发表
✅ 使用 **Matplotlib** 生成的PNG
- 高分辨率（300 DPI）
- 兼容LaTeX
- 文件小

### 2. 团队协作者演示
✅ 使用 **Plotly** 生成的HTML
- 可交互探索
- 易于分享
- 专业外观

### 3. 网页嵌入
✅ 使用 **Plotly** HTML
```html
<iframe src="path_3d_interactive.html" width="100%" height="600px"></iframe>
```

### 4. Jupyter Notebook
✅ 两者皆可
```python
# Matplotlib
%matplotlib inline
viz_matplotlib.plot_path_3d(path, cost_map)

# Plotly
fig = viz_plotly.plot_path_3d_interactive(path, cost_map)
fig.show()  # 直接在notebook中显示
```

---

## 🎓 技术细节

### Matplotlib实现
- **模块**: `utils/path_visualizer.py`
- **类**: `PathVisualizer`
- **依赖**: matplotlib, seaborn, mpl_toolkits.mplot3d
- **输出**: PNG (300 DPI)

### Plotly实现
- **模块**: `utils/interactive_visualizer.py`
- **类**: `InteractiveVisualizer`
- **依赖**: plotly
- **输出**: HTML (含JavaScript)

### 统一接口
```python
from utils import PathVisualizer, InteractiveVisualizer

# 静态
static_viz = PathVisualizer(output_dir="output")

# 交互
interactive_viz = InteractiveVisualizer(output_dir="output")
```

---

## 📚 相关文档

- **[utils/README.md](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\utils\README.md)** - 工具模块说明
- **[examples/demo_interactive_visualization.py](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\examples\demo_interactive_visualization.py)** - 交互式可视化演示
- **[experiments/README.md](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\experiments\README.md)** - 实验说明

---

## 🚀 下一步

1. ✅ **运行演示**: `uv run python examples/demo_interactive_visualization.py`
2. ✅ **运行实验**: 查看生成的HTML文件
3. ✅ **自定义**: 根据需要调整颜色和样式
4. ✅ **分享**: 将HTML文件发送给团队成员

---

**记住**: 
- 📄 **论文/报告** → 使用Matplotlib PNG
- 🌐 **演示/协作** → 使用Plotly HTML

---

**最后更新**: 2026-04-27  
**作者**: AI Code Assistant
