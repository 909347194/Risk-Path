# Results — 实验输出

所有实验的图表、数据、论文图表统一存放于此。

## 目录结构

```
results/
├── README.md                    # 本文件
│
├── paper_figures/               # ★ 论文最终图表 (300 DPI, 英文标注)
│   ├── fig1_temporal/           #   Fig1: 时间节律自适应性
│   ├── fig2_microclimate/       #   Fig2: 微气象-地形耦合
│   ├── fig3_pareto/             #   Fig3: 噪声-安全 Pareto
│   └── fig4_storm/              #   Fig4: 风暴窗口效应
│
├── exp1_temporal/               # Exp1 原始输出
├── exp2_microclimate/           # Exp2 原始输出
├── exp3_pareto/                 # Exp3 原始输出
├── exp4_storm/                  # Exp4 原始输出
├── exp5_comprehensive/          # Exp5 原始输出
│
├── tables/                      # 汇总表格 (CSV)
├── grid_system/                 # 网格系统可视化
└── synthetic_data/              # 合成数据可视化
```

## 生成方式

```bash
# 1. 运行各实验 (生成原始输出)
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1_temporal.run_exp1_temporal_adaptability
# ... 其他实验类似

# 2. 生成论文图表 (汇总到 paper_figures/)
uv run python -m methods.spatiotemporal_heterogeneity.experiments.common.paper_figures
```
