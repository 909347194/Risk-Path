# experiments/ — 实验目录

> **两条原则**
> 1. **配置跟着实验走**：每个实验目录自带 `config.yaml`；`configs/` 只留跨实验共享配置（`common.yaml`）。
> 2. **产物分级**：`result/` 是入库交付物（图 + CSV + 配置快照），`output/` 是本地 scratch（已 gitignore）。

## 1. 目录职责

```text
experiments/
├── README.md                  ← 本文件：组织约定
├── _template/                 ← 实验脚手架（模块化结构，复制改名即用）
├── Experiment 1_spatiotemporal_heterogeneity_characterization/
│                              ← 已有实验：时空异质性表征（证据链第 1 环）
└── viz_data/                  ← 数据可视化工具集（不是实验，无 run.py 流水线）
```

| 目录 | 是什么 | 怎么跑 |
|---|---|---|
| `_template/` | 新实验起点，含全部通用件 | 复制后改写 |
| `Experiment N_<主题>/` | 一个完整实验（配置 + 代码 + 产物） | `python3 run.py` |
| `viz_data/` | 各类数据的独立可视化脚本，一个数据类型一个 | 逐个脚本运行 |

## 2. 模块化结构契约（每个实验目录）

**职责分离，勿把逻辑堆回 `run.py`。**

| 文件 | 职责 | 改动频率 |
|---|---|---|
| `run.py` | **纯编排**：网格 → 数据 → 风险张量 → 规划 → 出图 → 导出 | 低 |
| `exp_common.py` | 路径引导（`HERE` / `MODULE_ROOT` / `RESULT_DIR`），保证模块单独 import 也能找到 `src/` | 不改 |
| `exp_config.py` | 配置加载，支持 `extends` 继承公共配置（实验值覆盖公共值） | 不改 |
| `exp_data.py` | 数据装配：真实数据**只读加载** / 合成管线切换 | 低 |
| `exp_planning.py` | 规划与路径度量（单次 TD-RiskA* + 路径指标）；**实验专属扫描逻辑追加在此** | 高 |
| `exp_metrics.py` | CSV 序列化 + 指标行构造；**实验专属统计追加在此** | 中 |
| `plot/figN_<主题>.py` | 全部可视化，每图一个模块，`__init__` 导出 `plot_figN`；**只画图不算数** | 高 |

参考实现：`Experiment 1_spatiotemporal_heterogeneity_characterization/`（权重敏感性扫描 + fig1–fig4 完整示例）。

## 3. 产物口径

| 目录 | 内容 | 入库 |
|---|---|---|
| `result/` | `fig*.png`、`*.csv`（metrics / sensitivity / path_difference …）、`_resolved_config.yaml` | ✅ 交付物 |
| `output/` | 中间产物、日志、临时缓存 | ❌ gitignore |
| `plot/` | 只放绘图**代码**，不放图片 | ✅ 代码 |

`_resolved_config.yaml` 是**合并后的配置快照**（继承 `common.yaml` 之后的实际生效值），
随结果一起入库，保证任何一张图都能追溯到当时的参数。

## 4. 配置约定（`config.yaml`）

```yaml
experiment:            # 名称 / 描述 / owner / created / seed
  name: exp1_...
data:
  type: real           # real | synthetic
spatial_grid:          # 传给 create_grid_from_config
  nx: 100
  ny: 100
  nz: 12
  resolution_xy: 48.459
  resolution_z: 10.0
time:
  total_slices: 96     # 时相数
  slice_minutes: 15    # 每时相分钟数
extends: ../../configs/common.yaml    # 可选：继承公共配置
params:                # 实验参数自定义（OD、出发时刻、权重、风情景…）
```

- 继承用 `extends:`，`exp_config.load_exp_config()` 递归合并，**实验值覆盖公共值**
- 跨实验才复用的参数才放 `configs/`，其余一律就地
- 内置的 `get_micro_grid()` / `get_macro_grid()` 只适合快速验证，**正式实验一律用自己目录的 config.yaml**

## 5. 数据口径（重要，别踩）

- 真实数据用 `exp_data.load_prepared_real_data()` **只读加载** `data/02_processed` 顶层已准备好的数组（带形状校验）。
- ⚠️ **不要跑 `DataPipeline(data_type='real').run_all()`**：它会从 `01_raw` 重算并**覆盖**已提交数据
  （实测重算结果与提交版本相对差 50%–90%，POI/人口全部不同）。实验必须用「准备好的」那份。

## 6. 新建实验

```bash
cd methods/spatiotemporal_heterogeneity/experiments
cp -r _template "Experiment 2_<主题>"
cd "Experiment 2_<主题>"
$EDITOR config.yaml       # 填参数（name/OD/时段/权重/风情景…）
$EDITOR README.md         # 目的 / 假设 / 方法 / 结果 / 结论
python3 run.py            # 产物落在 result/
```

**命名**：`Experiment <N>_<主题小写下划线>`（沿用现状，如 `Experiment 1_spatiotemporal_heterogeneity_characterization`）。
同一实验的迭代用版本后缀 `_v2` 开新目录，**不要覆盖旧目录**（结论要可追溯）；探索性实验可加前缀 `scratch_`。
目录名含空格是现状，代码里一律用 `Path` 拼路径，不要手拼字符串。

**实验记录**：每个实验目录的 `README.md` 按 `_template/README.md` 的七段写（目的 / 假设 / 配置要点 / 方法 / 运行 / 结果 / 结论），
跑完把关键数字填回第 6 节——README 和 `result/` 一起入库，是实验的可复现凭证。

## 7. viz_data/（可视化工具集）

一个数据类型一个脚本，自包含可单独运行，**只 `plt.show()` 不落盘**：

| 脚本 | 内容 |
|---|---|
| `viz_landuse_map.py` / `viz_building_heights.py` / `viz_buildings_raw.py` | 土地利用、建筑高度、原始建筑面 |
| `viz_road_mask.py` / `viz_population.py` / `viz_poi_counts.py` | 路网、人口、五类 POI |
| `viz_travel.py` / `viz_tidal.py` / `viz_tidal_anim.py` | 出行、潮汐快照、潮汐动画（96 时相） |
| `viz_landcover.py` | GLC 土地覆盖 + 不透水面 |
| `01visualize_grid_system.py` | 网格系统 3D；默认不落盘，`--save` 才写 `output/统计/` |

各数据数组轴序统一 `[ix, iy]`（经度在前），显示需 `arr.T` + `origin="lower"`。

## 8. 历史说明

- `configs/micro_experiment.yaml`、`configs/macro_case_study.yaml` 已在 `58c5881` 移除（"drop legacy configs"），
  场景配置改为各实验自带；`configs/common.yaml` 保留为公共参数。
- 早期本文件写的 `visualization/` 已更名 `viz_data/`；产物目录由统一 `output/` 细化为
  `result/`（入库）+ `output/`（本地）两级。
- `_template/` 已从单文件 `run.py` 回填为模块化结构（`exp_*/` + `plot/`），见提交 `767dbcc`、`bb41a39`。
