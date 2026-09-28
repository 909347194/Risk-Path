# 数据 × 方法适配分析（v2 · 2026-09-28 刷新）

> 范围：`methods/spatiotemporal_heterogeneity/src`（data_provision → tensor_engine → algorithms）
> v1（09-27）基于旧数据层；v2 通读了 09-27~28 的 10 个提交（情景风/雨、噪声可调、
> build_real_processed v2、GLC 交叉验证、实验模块化）后刷新。与 `docs/DATA_STATUS.md` 对账。

## 1. 方法的数据契约（src 硬性要求）

| 组件 | 输入 | 形状/单位 |
|---|---|---|
| `GridSystem`（macro） | — | **100×100×12×96**，dx=dy=50m、dz=10m、15min/步 |
| `build_risk_tensors` | landuse / building_heights / rho_population / rho_vehicle / wind_field / rain_data | (100,100) / (100,100) / (100,100,96)×2 / 风可 4D / 雨 (100,100,96) |
| `wind_environment`（scenario） | 配置节 `wind_environment` | 输出 (nx,ny,nz,nt) m/s，`is_observed:false` |
| `rain_environment`（scenario） | 配置节 `rain_environment` | 输出 (nx,ny,nt) mm/h |
| `SpatiotemporalTidalModel` | base_pop、poi_counts、N_total | 质量守恒密度场，S_cell=2500m² |
| `algorithms/a_star + env_tensor` | 四张 4D 张量 | (100,100,12,96) |

## 2. 数据资产现状（对账 `DATA_STATUS.md`，全部形状与网格对齐 ✅）

02_processed 已齐全：landuse(v2) / building_heights / road_mask / base_pop_2d / poi_counts /
rho_pop_3d / rho_vehicle_3d / travel_user_counts / base_vehicle_2d / GLC 校验基准，外加
03_tensors 的情景风（wind_speed_4d, nx,ny,nz,nt）。

**跨矩阵对齐实证（本报告新增）**：对 6 组配对做了正常 vs y 翻转相关性对比，
正常方向全面胜出（住宅用地×住宅POI 相关 **0.972**，商办×POI 0.976），
**无 y 镜像错位**（v2 处理的"y 镜像 bug 修复"已生效且各矩阵一致）。

**质量守恒实证**：rho_pop 每时相总量恒等 223.089 → **N_total_pop = 557,724**；
rho_vehicle → **N_total_veh = 227,225**。

## 3. 逐项适配结论（v2 更新）

| 数据 | v1 | v2 | 说明 |
|---|---|---|---|
| landuse | ✅ | ✅ | v2 = 建筑烧录 + GLC 回填，GLC 一致率 81.1% |
| poi_counts | ✅⚠️ | ⚠️ | 形状/分类 ✅；**口径问题见 §4-3** |
| building_heights | ✅ | ✅ | 修正 y 镜像后 all_touched 版，覆盖 93.2% |
| base_pop / rho_* | ⏳ | ✅ | 已生成且守恒；N_total 已实证 |
| travel | ✅ | ✅ | 校准/校验用；10 时段→96 步的曲线拟合仍开放（§4-2） |
| **weather** | ❌ | ✅ | **情景风 4D + 情景雨已接入 assembler**（`is_observed:false`，防误当观测）；真实 ERA5 降级为"可选验证数据" |

## 4. 剩余待办（按优先级）

1. **【中】数据处理链三足鼎立**：`build_real_processed.py`（v2 权威）vs `DataPipeline.run_all()`
   （会覆盖 02_processed，实测偏差 50-90%，exp_data 已绕开）vs `scripts/build_*`（v1，本助手 09-27 产物）。
   建议：明确 `build_real_processed.py` 为唯一口径，把 v1 脚本标注 superseded 或移入 `scripts/archive/`，
   并给 `run_all` 加"写回保护"（如 real 模式默认 `save=False` 或写 `02_processed/_recomputed/`）。
2. **【中】travel 时段→NT=96**：信令 10 切片的模式占比曲线（pt_drive 27%→75%）尚未用于
   拟合 `traffic_activation/population_activation`（当前仍为经验高斯）。拟合后潮汐相位可写进论文。
3. **【低】物理尺度**：bbox 4770×4830m vs 标称 5000×5000m（dx=50m），各向异性 ~5%、
   S_cell 2500 vs 实际 ~2304m²（-8%）。正式实验要么把 bbox 归一到 5km，要么改 dx/dy。
4. **【低】N_total 口径说明**：N_total_pop=557,724 vs WorldPop 合计 518,221（+7.6%）——
   如为有意放大（如昼夜人口）请在 DATA_STATUS 注明依据；否则建议对齐。

## 5. 结论

**数据层与方法完全适配，可以跑正式实验。** v1 报告的"气象硬缺口"已被情景风/雨模型解决
（真实 ERA5 转为可选增强）；N_total 已校准并实证守恒；全矩阵对齐无镜像问题。
剩余为 2 中 2 低的工程收口项，不影响实验开工。
