# experiments/ — 实验目录约定

> **原则：配置跟着实验走。** 每个实验一个目录，自己的配置写在自己目录下的 `config.yaml`；
> `configs/` 只保留**跨实验共享**的配置（如 `common.yaml` 的风险模型、POI 权重等公共参数）。

## 目录结构

```text
experiments/
├── README.md                 ← 本文件：组织约定
├── _template/                ← 新实验脚手架（复制改名即可）
│   ├── config.yaml           ← 实验专属配置（必须）
│   ├── README.md             ← 实验记录（目的/方法/结论，必须）
│   ├── run.py                ← 实验入口（可换成 scripts/）
│   └── output/               ← 产物，已 gitignore，不入库
├── visualization/            ← 可视化实验（已有）
│   ├── config.yaml
│   └── *.py                  ← 各数据类型独立脚本
└── <新实验目录>/              ← 一个实验一个目录
```

## 新建实验

```bash
cd methods/spatiotemporal_heterogeneity/experiments
cp -r _template <实验名>          # 例如 cp -r _template tidal_sensitivity_v1
cd <实验名>
$EDITOR config.yaml               # 填实验参数
$EDITOR README.md                 # 写实验目的/预期/结论
python3 run.py                    # 跑起来
```

## 命名规范

- 目录名：`<主题>_<方法>[_<版本>]`，小写 + 下划线，如 `crash_prob_montecarlo_v2`
- 同一方法的迭代实验用版本后缀 `_v1/_v2`，不要覆盖旧目录（实验结果要可追溯）
- 临时/探索性实验加前缀 `scratch_`，稳定后再改名

## 配置约定（config.yaml）

必备两段：

```yaml
spatial_grid:          # 传给 create_grid_from_config
  nx: 100              #   方式A：直接给 nx/ny/nz
  ny: 100
  nz: 12
  resolution_xy: 48.459   #   或方式B：给 x_min/x_max/resolution_xy 自动算
  resolution_z: 10.0

time:
  total_slices: 96     # 时相数
  slice_minutes: 15    # 每时相分钟数
```

其余节（如 `experiment:`、模型参数、数据路径）自定义，`create_grid_from_config` 会忽略。

**继承公共配置**：`extends: ../../configs/common.yaml`，入口脚本用 `load_config()` 合并（见 `run.py`），
实验值覆盖公共值。跨实验才需要复用的参数才放 `configs/`，其余一律就地。

## 加载方式

```python
from pathlib import Path
from tensor_engine.grid_system import create_grid_from_config

HERE = Path(__file__).resolve().parent
grid = create_grid_from_config(HERE / "config.yaml")   # 用自己目录的配置
```

`src/tensor_engine/grid_system.py` 的 `get_micro_grid()` / `get_macro_grid()` 是内置默认尺度，
只适合快速验证；**正式实验一律用自己目录的 config.yaml**。

## 历史说明

旧的 `configs/micro_experiment.yaml`、`configs/macro_case_study.yaml` 已在提交 `58c5881` 移除
（"drop legacy configs"），场景配置改为由各实验自带；`configs/common.yaml` 保留为公共参数。
