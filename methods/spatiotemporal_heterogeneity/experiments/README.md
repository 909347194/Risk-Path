# Experiments — 微观机制验证实验

## 目录结构

```
experiments/
├── common/                          # 共享工具
│   ├── scenario_builder.py          #   场景构建器 (Exp1~3 共用)
│   └── paper_figures.py             #   论文级图表生成
│
├── exp1_temporal/                   # Exp1: 时间节律自适应性
│   └── run_exp1_temporal_adaptability.py
│
├── exp2_microclimate/               # Exp2: 微气象-地形耦合避让
│   └── run_exp2_microclimate_terrain.py
│
├── exp3_pareto/                     # Exp3: 噪声-安全 Pareto 权衡
│   └── run_exp3_noise_safety_pareto.py
│
├── exp4_storm/                      # Exp4: 风暴窗口 + Label-Setting
│   └── run_exp4_pruning_efficiency.py
│
└── exp5_comprehensive/              # Exp5: 综合实验 + 鲁棒性
    ├── run_micro_comprehensive.py   #   基线/敏感性/统计/Scaling
    └── run_random_od_pareto.py      #   随机 OD Pareto 鲁棒性
```

## 运行方式

```bash
cd Risk-Path

# Exp1: 时间节律
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp1_temporal.run_exp1_temporal_adaptability

# Exp2: 微气象耦合
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp2_microclimate.run_exp2_microclimate_terrain

# Exp3: Pareto 权衡
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp3_pareto.run_exp3_noise_safety_pareto

# Exp4: 风暴窗口
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp4_storm.run_exp4_pruning_efficiency

# Exp5: 综合实验
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp5_comprehensive.run_micro_comprehensive
uv run python -m methods.spatiotemporal_heterogeneity.experiments.exp5_comprehensive.run_random_od_pareto

# 论文图表 (需要先运行上述实验)
uv run python -m methods.spatiotemporal_heterogeneity.experiments.common.paper_figures
```

## 输出位置

所有输出统一写入 `results/` 目录（见 `results/README.md`）。
