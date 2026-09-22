# analysis — 结果分析绘图（拆分组织）

针对结果分析图的 6 项缺口审计，本包优先补齐最紧迫的 3 项（直接对应论文
三个核心主张），并按"一脚本一主题"拆分组织，避免全部堆进单一脚本。

## 缺口 → 脚本 → 产出对照

| 缺口 | 脚本 | 产出（`results/analysis_figures/`） | 数据源 |
| --- | --- | --- | --- |
| 缺口1 沿路径累积风险缺分量逐步分解 | `plot_risk_decomposition.py` | `risk_decomposition/figA1_risk_decomposition.png`（堆积分解+逐步增量）<br>`.../figA2_risk_decomposition_timeslots.png`（分时次小多图）<br>`.../figA3_risk_composition_summary.png`（分量终值/构成占比） | `results/exp1_temporal/paths.json`（逐步 states） |
| 缺口3 安全约束缺满足可视化 | `plot_constraint_satisfaction.py` | `constraint_satisfaction/figB_constraint_satisfaction.png`（存活/净空/垂直速率/满足度矩阵）<br>`.../constraint_margins.csv`（逐步裕度明细） | `paths.json` + 合成场景建筑高度（seed=42） |
| 缺口4 基线对比缺系统对比图 | `plot_baseline_comparison.py` | `baseline_comparison/figC1_baseline_quality.png`（存活/致死/噪声+改进热力图）<br>`.../figC2_baseline_efficiency.png`（时间/节点/路径长度+综合雷达）<br>`.../baseline_summary.csv` | `results/exp5_comprehensive/baseline_comparison.csv`、`statistical_significance.csv` |

## 模块拆分原则

```
analysis/
├── _common.py                        # 只做 IO / 样式 / 参数常量，无图表逻辑
├── plot_risk_decomposition.py        # 缺口1：风险分量逐步分解
├── plot_constraint_satisfaction.py   # 缺口3：约束满足
├── plot_baseline_comparison.py       # 缺口4：基线对比
├── run_all.py                        # 编排入口（不写业务）
└── README.md
```

- 每个 `plot_*.py` 可独立运行、独立出图；新增缺口时**加新文件**，不要往
  现有脚本里塞第二种图。
- 共享口径（配色、算法顺序、参数常量、CSV/JSON 解析）全部收敛到 `_common.py`。
- 实验参数常量（`MICRO_GRID` / `CONSTRAINTS`）与
  `experiments/common/scenario_builder.py` 保持一致，改动需两处同步。

## 运行

```bash
cd methods/spatiotemporal_heterogeneity/experiments/analysis

python run_all.py                       # 一次性生成缺口1/3/4 全部图
python run_all.py --only 缺口1          # 只跑某一个

# 或单独运行（各脚本支持 --paths / --baseline / --out 覆盖默认输入输出）
python plot_risk_decomposition.py
python plot_constraint_satisfaction.py
python plot_baseline_comparison.py
```

依赖：`numpy`、`matplotlib`（与仓库 `pyproject.toml` 声明一致）。

## 尚未覆盖（后续按同结构各加独立脚本）

| 缺口 | 计划脚本（待补） |
| --- | --- |
| 3D 风险体中的路径展示 | `plot_paths_3d_volume.py` |
| 时变动态（动画/时间滑块） | `plot_temporal_animation.py`（或 `make_temporal_slider.py`） |
| 完整 Pareto 展示（非 2D 投影） | `plot_pareto_full.py` |
