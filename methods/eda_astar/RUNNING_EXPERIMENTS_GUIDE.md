# 实验脚本运行指南

**创建时间**: 2026-04-27  
**状态**: ✅ **可用**

---

## 📍 重要提示：运行目录

**所有实验脚本必须在 `src/EDAcostAstar/` 目录下运行！**

### ❌ 错误的运行方式
```bash
# 在项目根目录运行（错误！）
cd E:\01Reproduction\RiskModel
uv run python experiments/experiment_01_standard_astar.py
# Error: No such file or directory
```

### ✅ 正确的运行方式
```bash
# 在 EDAcostAstar 目录运行（正确！）
cd E:\01Reproduction\RiskModel\src\EDAcostAstar
uv run python experiments/experiment_01_standard_astar.py
```

---

## 🚀 快速开始

### 方法1: 使用 PowerShell 命令

```powershell
# 切换到正确目录
cd E:\01Reproduction\RiskModel\src\EDAcostAstar

# 运行实验1: Standard Cost A*
$env:PYTHONIOENCODING="utf-8"; uv run python experiments/experiment_01_standard_astar.py

# 运行实验2: Original EDA-A*
$env:PYTHONIOENCODING="utf-8"; uv run python experiments/experiment_02_original_eda.py

# 运行实验3: Two-Stage EDA-CostA*
$env:PYTHONIOENCODING="utf-8"; uv run python experiments/experiment_03_two_stage_eda.py

# 运行实验4: Algorithm Comparison
$env:PYTHONIOENCODING="utf-8"; uv run python experiments/experiment_04_comparison.py
```

### 方法2: 使用 VS Code 终端

1. 在 VS Code 中打开 `src/EDAcostAstar/` 文件夹
2. 打开终端（Terminal → New Terminal）
3. 直接运行：
   ```bash
   uv run python experiments/experiment_01_standard_astar.py
   ```

### 方法3: 使用批处理脚本（推荐）

创建 `run_experiments.bat` 文件：

```batch
@echo off
cd /d %~dp0
echo Running Experiment 1: Standard Cost A*...
uv run python experiments/experiment_01_standard_astar.py
pause
```

---

## 📊 实验列表

| 实验编号 | 脚本名称 | 算法 | 预计时间 | 输出目录 |
|---------|---------|------|---------|---------|
| 1 | experiment_01_standard_astar.py | Standard Cost A* | ~5分钟 | output/experiment_01/ |
| 2 | experiment_02_original_eda.py | Original EDA-A* | ~10分钟 | output/experiment_02/ |
| 3 | experiment_03_two_stage_eda.py | Two-Stage EDA-CostA* | ~15分钟 | output/experiment_03/ |
| 4 | experiment_04_comparison.py | 三种算法对比 | ~30分钟 | output/experiment_04_comparison/ |

---

## 🔧 常见问题

### Q1: "No such file or directory" 错误

**原因**: 在错误的目录运行脚本

**解决**: 
```bash
cd E:\01Reproduction\RiskModel\src\EDAcostAstar
uv run python experiments/experiment_01_standard_astar.py
```

### Q2: "ModuleNotFoundError" 错误

**原因**: Python路径未正确配置

**解决**: 确保在 `src/EDAcostAstar/` 目录运行，脚本会自动添加项目根目录到 `sys.path`

### Q3: UnicodeEncodeError 错误

**原因**: Windows PowerShell默认GBK编码

**解决**: 
```powershell
$env:PYTHONIOENCODING="utf-8"; uv run python experiments/experiment_01_standard_astar.py
```

### Q4: 依赖库缺失

**解决**: 
```bash
cd E:\01Reproduction\RiskModel
uv sync
```

---

## 📁 输出文件位置

所有实验结果保存在 `output/` 目录下：

```
src/EDAcostAstar/output/
├── experiment_01/           # Standard A* 结果
│   ├── path_visualization.png
│   └── cost_map_slices.png
├── experiment_02/           # Original EDA 结果
│   ├── path_visualization.png
│   └── eda_convergence.png
├── experiment_03/           # Two-Stage EDA 结果
│   ├── path_visualization.png
│   ├── clustering_results.png
│   └── heuristic_analysis.png
└── experiment_04_comparison/# 对比结果
    ├── path_comparison.png
    └── performance_comparison.png
```

---

## 💡 最佳实践

### 1. 使用绝对路径
```powershell
# 推荐：使用绝对路径
cd E:\01Reproduction\RiskModel\src\EDAcostAstar
```

### 2. 设置环境变量
```powershell
# 在 PowerShell 配置文件 ($PROFILE) 中添加
$env:PYTHONIOENCODING = "utf-8"
```

### 3. 创建快捷方式
在桌面创建快捷方式，指向：
```
C:\Windows\System32\cmd.exe /K "cd /d E:\01Reproduction\RiskModel\src\EDAcostAstar"
```

### 4. 使用 VS Code Workspace
创建 `.code-workspace` 文件：
```json
{
  "folders": [
    {
      "path": "src/EDAcostAstar"
    }
  ],
  "settings": {
    "terminal.integrated.cwd": "${workspaceFolder}"
  }
}
```

---

## 🎯 验证安装

运行以下命令验证环境配置：

```bash
cd E:\01Reproduction\RiskModel\src\EDAcostAstar

# 检查Python版本
python --version

# 检查uv
uv --version

# 测试导入
uv run python -c "from core import Grid3D, IntegratedCostModel; print('✓ Imports OK')"

# 运行简单测试
uv run python tests/test_fatality_risk.py
```

---

## 📝 相关文档

- **[experiments/README.md](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\experiments\README.md)** - 实验详细说明
- **[utils/README.md](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\utils\README.md)** - 工具模块说明
- **[README.md](file://e:\01Reproduction\RiskModel\src\EDAcostAstar\README.md)** - 项目主文档

---

**记住：始终在 `src/EDAcostAstar/` 目录下运行实验脚本！** ✨

---

**最后更新**: 2026-04-27  
**作者**: AI Code Assistant
