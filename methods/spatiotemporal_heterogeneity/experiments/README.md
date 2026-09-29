# experiments/ — 实验目录约定

> **原则：配置跟着实验走。** 每个实验一个目录，自己的配置写在自己目录下的 `config.yaml`；
> `configs/` 只保留**跨实验共享**的配置（如 `common.yaml` 的风险模型、POI 权重等公共参数）。
> **可视化归 `plot/`，run.py 只做编排。**

## 目录结构

```text
experiments/
├── README.md                 ← 本文件：组织约定
├── _template/                ← 新实验脚手架（复制改名即可，模块化结构）
│   ├── run.py                ← 入口：纯编排（网格→数据→张量→规划→出图→导出）
│   ├── exp_common.py         ←   路径引导（HERE / MODULE_ROOT / RESULT_DIR）
│   ├── exp_config.py         ←   配置加载（extends 继承）
│   ├── exp_data.py           ←   数据装配（真实数据只读加载 / 合成切换）
│   ├── exp_planning.py       ←   规划与路径度量（实验专属扫描追加在此）
│   ├── exp_metrics.py        ←   CSV 指标导出（实验专属统计追加在此）
│   ├── plot/                 ←   全部可视化：每图一个模块，__init__ 导出 plot_figN
│   ├── config.yaml           ←   实验专属配置（必须）
│   └── README.md             ←   实验记录（目的/方法/结论，必须）
├── Exp1_spatiotemporal_heterogeneity_characterization/
│                             ← 参考实现（权重敏感性扫描与 fig1–4 完整示例）
│   ├── run.py + exp_*.py + plot/ + config.yaml + README.md
│   └── results/              ← 运行产物（本地产物，已 gitignore，不入库）
├── viz_data/                 ← 数据可视化脚本集（landuse/POI/人口/建筑/landcover 预览图）
└── <新实验目录>/
```

## 模块结构（职责分离，勿把逻辑堆回 run.py）

| 文件 | 职责 | 说明 |
|---|---|---|
| `run.py` | 纯编排 | 网格→数据→风险张量→规划→出图→导出，只调用下面各层 |
| `exp_common.py` | 路径引导 | 保证任意模块单独 import 都能找到 `src/` |
| `exp_config.py` | 配置 | `load_exp_config()`，支持 `extends` 继承公共配置 |
| `exp_data.py` | 数据 | 真实数据**只读加载** `load_prepared_real_data()` |
| `exp_planning.py` | 规划 | `plan_one` / 路径度量；实验专属扫描逻辑追加在此 |
| `exp_metrics.py` | 指标 | CSV 序列化 + 通用指标行；实验专属统计追加在此 |
| `plot/` | 可视化 | **每图一个模块**（`figN_<主题>.py`），只画图、不算数、不做 IO |

## 新建实验

```bash
cd methods/spatiotemporal_heterogeneity/experiments
cp -r _template "Exp<N>_<主题>"       # 见命名规范
cd "Exp<N>_<主题>"
$EDITOR config.yaml                   # 填实验参数（params / data / extends）
$EDITOR README.md                     # 写实验目的/预期/结论
python3 run.py                        # 跑起来
```

## 命名规范

- **实验目录**：`Exp<N>_<主题>`（与 Exp1 一致；N 递增，主题下划线分词，如 `Exp2_pareto_tradeoff`）
- 同一实验的迭代用目录名后缀 `_v1/_v2`，不要覆盖旧目录（实验结果要可追溯）
- 临时/探索性实验加前缀 `scratch_`，稳定后并入正式命名
- 可视化脚本集放 `viz_data/`；实验专属图放实验自己的 `plot/`

## 配置约定（config.yaml）

必备两段：

```yaml
spatial_grid:          # 传给 create_grid_from_config
  nx: 100              #   方式A：直接给 nx/ny/nz
  ny: 100
  nz: 12
  resolution_xy: 48.459   #   研究区实测格宽（勿用 50 的旧标称值）
  resolution_z: 10.0

time:
  total_slices: 96     # 时相数
  slice_minutes: 15    # 每时相分钟数
```

其余节（如 `experiment:`、`params:`、数据开关）自定义，`create_grid_from_config` 会忽略。

**继承公共配置**：`extends: ../../configs/common.yaml`，入口用 `exp_config.load_exp_config()`
合并（实验值覆盖公共值）。跨实验才需要复用的参数放 `configs/`，其余一律就地。

## 产物约定

| 目录 | 入库 | 用途 |
|---|---|---|
| `results/` | ❌ gitignore | 运行产物（图、指标 CSV）。需要进论文/报告时另行摘录到 `docs/` |
| `output/` | ❌ gitignore | 草稿/中间输出 |
| `result/_resolved_config.yaml` | ✅ | **配置快照**建议随实验记录归档（保证可复现） |

## 数据口径

- 真实数据一律**只读加载** `data/02_processed` 已准备的数组（`exp_data.load_prepared_real_data`）。
  `DataPipeline(real).run_all()` 自带**写回保护**（`allow_overwrite=False` 默认拒绝覆盖已校验数据，
  见 `docs/SRC_REVIEW_20260928.md` M1）；确需重算时显式传 `allow_overwrite=True` 并自行备份。
- 网格常量（BBOX/NX/NY）统一从 `scripts/grid_constants.py` 取，勿在实验内硬编码。
- 数据清单与处理口径见 `../docs/DATA_STATUS.md`。

## 历史说明

- 旧 `configs/micro_experiment.yaml`、`configs/macro_case_study.yaml` 已在 `58c5881` 移除
  （场景配置改由各实验自带）；`configs/common.yaml` 保留为公共参数。
- 早期 `visualization/` 目录（数据预览脚本）已演进为 `viz_data/`。
- `_template/` 于 2026-09-28 回填模块化结构（exp_*/plot/），以 Exp1 为参考实现。
- 目录 `Experiment 1_…` 更名为 `Exp1_…`；产物目录 `result/` 更名 `results/` 并出库
  （提交 `ea0f38a` / `e832550`）。
- 数据处理脚本经 `cb864fa` 统一口径：每环节仅保留当前项目版本；网格常量抽出为
  `scripts/grid_constants.py`（原 `build_landuse_map.py` 已并入 `refine_landuse_map.py` 链路）。
