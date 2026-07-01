# Data Provision Pipeline

本文档固定 `src/data_provision` 的职责边界和数据流。后续写代码时先看这份文档，避免把合成城市、张量生成、路径规划、可视化混在一起。

## 1. 本层职责

`data_provision` 只做一件事：

```text
真实或合成的地理数据 -> 对齐到统一网格的 NumPy 矩阵
```

本层不负责：

- 生成 `P_crash`、噪声成本、伤亡成本等风险张量。
- 运行 A*、EDA、K-means 或路径规划。
- 生成论文图。

这些分别属于：

- `src/tensor_engine`
- `src/algorithms`
- `src/visualization`

## 2. 合成/真实数据切换

本层支持一键切换合成数据和真实数据处理模式。

### 路径约定

```
data/
├── 01_raw/                  # 真实数据原始 GIS 输入
│   └── synthetic/            # 合成数据原始 GIS 输入
├── 02_processed/             # 真实数据处理后的 NumPy 矩阵
│   └── synthetic/            # 合成数据处理后的 NumPy 矩阵
└── 03_tensors/               # 真实数据张量输出
    └── synthetic/            # 合成数据张量输出
```

合成数据的路径结构中始终包含 `synthetic` 子目录。

### 全局切换

```python
from data_provision import set_data_type

# 切换到合成数据模式
set_data_type('synthetic')

# 切换到真实数据模式
set_data_type('real')
```

### 路径获取

```python
from data_provision.paths import get_data_paths

paths = get_data_paths()  # 基于当前数据类型
print(paths.processed)    # data/02_processed/ 或 data/02_processed/synthetic/
print(paths.base_pop_path)  # 自动定位 base_pop_2d.npy
```

## 3. Pipeline 一键运行

```python
from data_provision.pipeline import DataPipeline

# 合成模式：一键处理所有数据
pipeline = DataPipeline(data_type='synthetic')
result = pipeline.run_all()

# 真实模式
pipeline = DataPipeline(data_type='real')
result = pipeline.run_all()

# 分步运行
pipeline = DataPipeline(data_type='synthetic')
pipeline.run_landuse()
pipeline.run_building()
pipeline.run_road()
pipeline.run_population()
pipeline.run_poi()
pipeline.run_tidal()
pipeline.run_weather()
result = pipeline.collect()
```

## 4. 文件架构

```
data_provision/
├── __init__.py                  # 统一导出，包含 set_data_type/get_data_paths
├── paths.py                     # 路径集中管理，合成/真实路径自动切换
├── pipeline.py                  # Pipeline 编排器，一键运行所有处理
├── landuse_builder.py           # 土地利用数据处理
├── building_processor.py        # 建筑高度数据处理
├── road_processor.py            # 道路网络数据处理
├── weather_processor.py         # 气象数据（风、降水）处理
├── population_resampler.py      # 人口数据（WorldPop/合成）处理
├── poi_parser.py                # POI（兴趣点）数据处理
├── spatiotemporal_tidal_model.py # 时空潮汐人口/车辆密度模型
└── DATA_PIPELINE.md             # 本文档
```

## 5. 推荐数据流

```text
synthetic_data_factory 或真实数据
  -> landuse_builder.py
      -> landuse_map.npy
  -> building_processor.py
      -> building_heights.npy
  -> road_processor.py
      -> road_mask.npy
  -> population_resampler.py
      -> base_pop_2d.npy
  -> poi_parser.py
      -> poi_counts.npz
  -> spatiotemporal_tidal_model.py
      -> rho_pop_3d.npy
      -> rho_vehicle_3d.npy
  -> weather_processor.py
      -> wind_field.npy (03_tensors)
      -> rain_data.npy  (03_tensors)
```

### 各阶段数据形状

```
landuse_map:      (nx, ny)       int32   土地利用编码
building_heights: (nx, ny)       float32 建筑高度 (m)
road_mask:        (nx, ny)       bool     道路掩码
base_pop_2d:      (nx, ny)       float32 基础人口密度
poi_counts.npz:   5 × (nx, ny)  float32  POI 类别计数
rho_pop_3d:       (nx, ny, nt)  float32 动态人口密度
rho_vehicle_3d:   (nx, ny, nt)  float32 动态车辆密度
wind_field:       (nx, ny, nt)  float32 风速 (m/s)
rain_data:        (nx, ny, nt)  float32 降雨强度 (mm/h)
```

高度维度不在本层扩展。若后续需要 `(nx, ny, nz, nt)`，由 `tensor_engine` 负责广播。

## 6. 文件职责

### `paths.py`

集中管理所有路径，支持合成/真实数据自动切换。

核心接口：
```python
set_data_type('synthetic' | 'real')
get_data_paths() -> DataPaths
DataPaths.processed       # 当前数据类型的 02_processed 目录
DataPaths.raw             # 当前数据类型的 01_raw 目录
DataPaths.tensors         # 当前数据类型的 03_tensors 目录
DataPaths.base_pop_path   # base_pop_2d.npy 路径
DataPaths.poi_counts_path # poi_counts.npz 路径
# ...更多文件路径属性
```

### `landuse_builder.py`

输入：
- 真实数据：Shapefile（含土地利用分类属性）
- 合成数据：`landuse_map.npy`（由 synthetic_data_factory 生成）

输出：
```text
data/02_processed[/synthetic]/landuse_map.npy
```

功能：
- 真实路径：使用 rasterio.features.rasterize 将 Shapefile 栅格化到目标网格
- 合成路径：直接加载预先导出的 .npy 文件

### `building_processor.py`

输入：
- 真实数据：Shapefile（含建筑高度属性）
- 合成数据：`building_heights.npy`

输出：
```text
data/02_processed[/synthetic]/building_heights.npy
```

功能：
- 真实路径：栅格化建筑足迹，每个网格单元记录最大建筑高度
- 合成路径：加载预生成数据
- 备用方案：从土地利用估计建筑高度（`estimate_building_heights_from_landuse`）

### `road_processor.py`

输入：
- 真实数据：Shapefile 道路网络
- 合成数据：`road_mask.npy`

输出：
```text
data/02_processed[/synthetic]/road_mask.npy
```

功能：
- 真实路径：将道路线要素栅格化为布尔掩码
- 合成路径：加载预生成数据

### `weather_processor.py`

输入：
- 真实数据：ERA5 NetCDF（含风场 u10/v10、降水 tp）
- 合成数据：`wind_field.npy`, `rain_data.npy`（位于 03_tensors/synthetic/）

输出：
```text
data/03_tensors[/synthetic]/wind_field.npy  (nx, ny, nt)
data/03_tensors[/synthetic]/rain_data.npy   (nx, ny, nt)
```

功能：
- 真实路径：使用 xarray 读取 NetCDF，插值到目标网格，重采样时间维度
- 合成路径：直接加载预生成张量

### `population_resampler.py`

输入：
- 真实数据：WorldPop `.tif`
- 合成数据：`landuse_2d`

输出：
```text
data/02_processed[/synthetic]/base_pop_2d.npy
```

功能：
- 真实路径：裁剪 WorldPop，并重采样到目标网格
- 合成路径：按土地利用语义生成基础人口底图

稳定入口：
```python
build_base_population(...)
create_synthetic_base_population(...)
resample_worldpop_to_grid(...)
load_base_population(...)
```

### `poi_parser.py`

输入：
- 真实数据：OSM/GeoJSON
- 合成数据：`landuse_2d`

输出：
```text
data/02_processed[/synthetic]/poi_counts.npz
```

内部包含：
```text
residential
office
institution
transport
industrial
```

功能：
- 真实路径：读取 OSM tags，并映射到 5 类 POI
- 合成路径：按土地利用语义生成 5 类 POI 计数图

稳定入口：
```python
build_poi_counts(...)
create_synthetic_poi_counts(...)
parse_osm_poi_geojson(...)
load_poi_counts(...)
```

### `spatiotemporal_tidal_model.py`

输入：
```text
base_pop_2d.npy
poi_counts.npz
```

输出：
```text
data/02_processed[/synthetic]/rho_pop_3d.npy
data/02_processed[/synthetic]/rho_vehicle_3d.npy
```

功能：
- 使用 POI 空间吸引力和 24 小时时间激活函数，生成动态人口密度
- 使用交通类权重和交通激活函数，生成动态车辆密度

稳定入口：
```python
SpatiotemporalTidalModel
build_dynamic_population_density(...)
build_dynamic_vehicle_density(...)
```

### `pipeline.py`

一键式 Pipeline 编排器，自动串联所有处理阶段。

核心入口：
```python
DataPipeline(data_type='synthetic' | 'real')
    .run_all() -> PipelineResult
```

分步控制：
```python
pipeline.run_landuse()
pipeline.run_building()
pipeline.run_road()
pipeline.run_population()
pipeline.run_poi()
pipeline.run_tidal()
pipeline.run_weather()
```

## 7. 与 tensor_engine 的对接

### 数据传递

`data_provision` 的输出文件路径遵循统一约定，`tensor_engine` 可通过相同路径规则读取：

```python
from data_provision.paths import get_data_paths

paths = get_data_paths('synthetic')
base_pop = np.load(paths.base_pop_path)
poi_counts = np.load(paths.poi_counts_path)
```

### 网格一致性

所有输出的空间形状均为 `(nx, ny)`，时间形状为 `(nx, ny, nt)`，与 `GridSystem` 完全对齐。

### 典型调用链路

```python
# 1. Data Provision
from data_provision import set_data_type, get_data_paths
from data_provision.pipeline import DataPipeline

set_data_type('synthetic')
pipeline = DataPipeline()
result = pipeline.run_all()

# 2. Tensor Engine
from tensor_engine import TensorBuilder, GridSystem

grid = GridSystem()
builder = TensorBuilder(grid=grid)
# builder 读取 data_provision 的输出构建风险张量
```

## 8. 真实数据模式

真实数据路径建议：
```text
data/01_raw/
├── worldpop_xxx.tif        # WorldPop 人口栅格
├── poi_data.geojson        # OSM POI
├── landuse.shp             # 土地利用
├── buildings.shp           # 建筑
├── roads.shp               # 道路
├── era5_wind_2020.nc       # ERA5 风场
└── era5_precip_2020.nc     # ERA5 降水
```
  worldpop.tif
  osm_poi.geojson
```

处理后输出：

```text
data/02_processed/
  base_pop_2d.npy
  poi_counts.npz
  rho_pop_3d.npy
  rho_vehicle_3d.npy
```

示意代码：

```python
from data_provision import (
    build_base_population,
    build_poi_counts,
    build_dynamic_population_density,
)
from tensor_engine.grid_system import get_macro_grid

grid = get_macro_grid()

base_pop = build_base_population(
    worldpop_tif="data/01_raw/worldpop.tif",
    grid=grid,
    city_bounds=(minx, miny, maxx, maxy),
)

poi_counts = build_poi_counts(
    geojson_path="data/01_raw/osm_poi.geojson",
    grid=grid,
    city_bounds=(minx, miny, maxx, maxy),
)

rho_pop = build_dynamic_population_density(grid=grid)
```

## 5. 合成数据模式

微观机制实验优先使用合成数据，因为它可控、可解释、便于证明模型机制。

示意代码：

```python
from data_provision import (
    create_synthetic_base_population,
    create_synthetic_poi_counts,
    SpatiotemporalTidalModel,
)
from tensor_engine.grid_system import get_micro_grid

grid = get_micro_grid()

base_pop = create_synthetic_base_population(grid=grid)
poi_counts = create_synthetic_poi_counts(grid=grid)

model = SpatiotemporalTidalModel(grid=grid)
rho_pop = model.build_population_density(base_pop, poi_counts)
rho_vehicle = model.build_vehicle_density(base_pop, poi_counts)
```

注意：这里的 `base_pop` 可临时作为 `base_vehicle` 的代理。正式实验建议用道路等级或 road mask 构造独立的车辆基础密度图。

## 6. 和 `utils/synthetic_data_factory` 的关系

推荐边界：

```text
utils/synthetic_data_factory
  负责合成城市语义底图：
    landuse
    road_mask
    building_heights
    weather
    od_pairs

src/data_provision
  负责把这些底图加工成统一输入：
    base_pop_2d
    poi_counts
    rho_pop_3d
    rho_vehicle_3d
```

不要在 `data_provision` 里重复实现完整合成城市生成器。`data_provision` 可以有简单 fallback，但主合成逻辑应逐步收敛到 `utils/synthetic_data_factory`。

## 7. 质量检查

每次修改 `data_provision` 后至少运行：

```powershell
python -m compileall -q methods\spatiotemporal_heterogeneity\src\data_provision
```

并检查：

```text
base_pop_2d.shape == (nx, ny)
poi_counts 每个类别 shape == (nx, ny)
rho_pop_3d.shape == (nx, ny, nt)
rho_vehicle_3d.shape == (nx, ny, nt)
所有数组无 NaN
所有密度非负
```

## 8. 不要提交的文件

以下文件是生成物，不应作为代码提交：

```text
data/02_processed/*.npy
data/02_processed/*.npz
src/**/__pycache__/
output/
```

这些文件可以通过脚本重新生成。

## 9. 当前最小闭环

先完成这个闭环，不要继续扩散：

```text
create_synthetic_base_population()
create_synthetic_poi_counts()
SpatiotemporalTidalModel.build_population_density()
SpatiotemporalTidalModel.build_vehicle_density()
```

当这条链稳定后，再接入：

```text
tensor_engine.dynamic_noise
tensor_engine.dynamic_p_crash
tensor_engine.tensor_builder
```
