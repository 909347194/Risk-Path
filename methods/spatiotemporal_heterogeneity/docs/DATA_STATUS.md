# 数据状态清单（spatiotemporal_heterogeneity）

> 更新：2026-09-27 · 由 `scripts/build_real_processed.py` 处理并校验

## 一、01_raw 原始数据

| 数据 | 文件 | 状态 | 说明 |
|---|---|---|---|
| 建筑五类面 | `building/*.shp`（5 套） | ✅ 20,670 栋 | Height 字段 1.2–224.5m，WGS84，label 1–5 |
| 路网 | `road/roadline_clip.shp` + `osm_roads.geojson` | ✅ 31,673 线段 | 双源合并使用 |
| 人口栅格 | `population/population.tif` | ✅ ~90m | WorldPop，总量 518,221 人（≈20,729/km²） |
| 土地覆盖 | `land_cover/land_cover.tif` | ✅ GLC_FCS30 10m | 交叉验证基准 |
| POI | `poi.geojson`（合成）+ OSM 抓取 | ✅ 21,082 点 | 5 类已标注 |
| 研究区范围 | `buildings_max_range/buildings_max_range.geojson` | ✅ | BBOX = 113.2911–113.3384°E, 23.0735–23.1169°N |
| 合成数据 | `synthetic/seed_42/` | ✅ | 5 件套完整 |
| LFS 残留指针 | `buildings_max_range.CPG`、`population.tif.aux.xml/.xml` | ⚪ 无影响 | 辅助元数据文件，不影响任何处理 |
| ERA5 风/雨 | — | ❌ 缺失 | `*wind*.nc` / `*rain*.nc` 待外部获取 |

## 二、02_processed 处理产物（全部 (100,100)，NaN=0）

| 产物 | 形状 | 校验 | 来源/处理 |
|---|---|---|---|
| `landuse_map.npy`（v2） | (100,100) int32 | ✅ GLC 一致率 81.1%，覆盖 99.2% | A+：建筑五类烧录 + GLC 回填 + 道路收紧 |
| `building_heights.npy` | (100,100) float32 | ✅ 建筑格覆盖 93.2%，p50=19.9m | 五类面 Height 烧录（all_touched + 格内最大值；修正 y 镜像 bug） |
| `road_mask.npy` | (100,100) bool | ✅ 5,909 格 | 格心距路网 ≤24m |
| `base_pop_2d.npy` | (100,100) float32 | ✅ 总量 518,221 | WorldPop 重采样（保总量、y 翻转对齐） |
| `poi_counts.npz` | 5×(100,100) | ✅ 2,834 POI | 多源合并（另有 osm 版 1,898） |
| `rho_pop_3d.npy` | (100,100,96) float32 | ✅ 质量守恒（各时相总量恒等 207.3） | POI 引力潮汐模型 |
| `rho_vehicle_3d.npy` | (100,100,96) float32 | ✅ | 同上（车流基数 base_vehicle_2d） |
| `travel_user_counts.npz` | 5×(100,100,10) | ✅ 659,734 出行 | 手机信令 4 模式 ×10 时段 |
| `base_vehicle_2d.npy` | (100,100) float32 | ✅ 418 格有值 | 出行数据派生 |
| `landcover_fcs10_100x100.npy` + `_impervious_frac` | (100,100) | ✅ | GLC 聚合（验证基准） |
| `landuse_map_b/c.npy` | (100,100) | ✅ | 交叉验证方案 B/C 存档 |

## 三、03_tensors 与缺口

| 项 | 状态 |
|---|---|
| **scenario `wind_speed_4d.npy`** | ✅ **默认风数据源**（新增）：`src/tensor_engine/wind_environment.py` 构建，`scripts/build_wind_environment.py` 落盘，`(nx,ny,nz,nt)` float32，m/s。`is_observed: false`（情景化合成，非真实风场） |
| `wind_environment_metadata.json` | ✅ 记录 model/scenario/各因子开关与 `is_observed:false`（防误当观测） |
| synthetic `wind_field/rain_data` | ⚪ legacy：保留 `weather_processor` 兼容入口，现已非默认路径 |
| real `wind_field.npy`/`rain_data.npy` | ❌ 可选：ERA5（u10/v10 + 降水，逐小时 0.25°），仅作 `real` 模式历史入口；**项目不再以 ERA5 为核心风场依赖** |
| `Cost_total(100,100,12,96)` | ✅ 可由 scenario 风 + 雨 + 峡谷直接组装（P_crash 的 Φ = f_wind·f_rain·f_obs 已通） |

> **风环境定位变更（2026-09-27）**：不再依赖/插值 ERA5 构造伪高分辨率真实风场。
> 改为情景化低空风环境 `V(x,y,z,t)=V_ref(t)·F_z(z)·F_urban(x,y)·F_gust(t)`，
> 含时间变化、高度修正、城市形态遮蔽衰减；默认确定性（gust 关闭）。
> 详见 `configs/common.yaml` 第 7 节与 `wind_environment.py` 顶部说明。

## 处理口径备注

1. 高度/土地利用统一用 `all_touched`（边界穿越）口径；高度取格内最大值（城市峡谷）。
2. 细栅格 row0=北、格网 iy0=南，池化时 y 必须镜像（曾出 bug，已修，见 git 历史）。
3. `road_mask`（5,909 格 = 路网邻域）与 `landuse==5`（2,436 格 = 无建筑的道路格）语义不同，后者是前者子集加 16 个 POI 交通功能格。
4. 潮汐模型质量守恒经校验：各时间片全图总量恒等。
