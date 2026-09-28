# 数据 × 方法适配分析（2026-09-27）

> 范围：`methods/spatiotemporal_heterogeneity/src`（data_provision → tensor_engine → algorithms）
> 问题：当前已整理的数据是否适合本方法？缺什么？哪里需要校准？

## 1. 方法的数据契约（src 硬性要求）

| 组件 | 输入 | 形状/单位 |
|---|---|---|
| `GridSystem`（macro） | — | **NX×NY×NZ×NT = 100×100×12×96**，dx=dy=50m、dz=10m、15min/步（24h） |
| `risk_tensor_assembler.build_risk_tensors` | landuse / building_heights / rho_population / rho_vehicle / wind_field / rain_data | 前两者 (100,100)；后四者 (100,100,96) |
| `DynamicCrashProbability` | wind、rain、building（SVF/峡谷 f_obs） | 风速/降雨强度，建筑高度 m |
| `DynamicFatalityModel` | rho_pop、rho_vehicle、flight_altitude | 人/车密度 |
| `dynamic_noise` | landuse（编码 0-6）+ population | 敏感度系数表 `landuse_code_map` |
| `SpatiotemporalTidalModel` | base_pop、poi_counts、N_total_pop/veh | 质量守恒密度场，S_cell=dx·dy=2500m² |
| `algorithms/a_star + env_tensor` | 四张 4D 风险张量 | (100,100,12,96) |

## 2. 数据资产盘点（02_processed，全部 (100,100) 对齐）

| 数据 | 形状 | 来源 | 状态 |
|---|---|---|---|
| landuse_map.npy | (100,100) | building 五类 shp + roadline_clip（LFS） | ✅ 主源 + B/C 交叉验证 |
| poi_counts.npz | 5×(100,100) | 百度 Agent Plan 2834 条 | ✅ |
| building_heights.npy | (100,100) | building shp `Height`（全覆盖，mean 24.7m，max 224.5m） | ✅ 今日补齐 |
| base_pop_2d.npy | (100,100) | population.tif（51.8 万人，58×54px@90m） | ✅ 今日补齐 |
| road_mask.npy | (100,100) bool | landuse==5 | ✅ 今日补齐 |
| travel_user_counts.npz | 4模式×(100,100,10) | 手机信令（论文数据） | ✅ 校验/校准用 |
| base_vehicle_2d.npy | (100,100) | travel pt_drive | ✅ |
| rho_pop / rho_vehicle | (100,100,96) | 潮汐模型（真实管线实跑产物） | ✅ 已跑通 |
| wind_field / rain_data | (100,100,96) | — | ❌ **唯一硬缺口** |

**端到端验证**：`DataPipeline(data_type='real')` 六阶段（landuse→building→road→pop→poi→tidal）
**全部跑通**，输出 rho_pop/rho_vehicle 形状正确 → **数据层与方法已对齐，可以进入实验**。

## 3. 逐项适配结论

| 数据 | 适配性 | 说明 |
|---|---|---|
| landuse | ✅ | 编码 0-6 与 `PROJECT_SPEC`/`dynamic_noise` 一致；A~B 一致性 35.5%（口径差异正常） |
| poi_counts | ✅ | 五分类与 `poi_weights` 精确对应；⚠️ 截断偏差→密度峰值平滑（相对格局可用） |
| building_heights | ✅ | Height 字段全覆盖、单位米；SVF/峡谷 f_obs 直接可用 |
| base_pop_2d | ✅ | WorldPop 口径（人/格）；真实总量 518,221 人 |
| travel | ✅（校准用） | 10 时段×4 模式；活跃格稀疏（429/10000）→ 只作校验/时间曲线校准，不满覆盖 |
| weather | ❌ | 无真实风场/降雨；**合成 fallback 是 micro 形状 (60,60,...)，不能直接用于 macro (100,100,96)** |

## 4. 正式实验前必须处理的 4 件事

1. **气象数据（唯一硬缺口）**：需要 (100,100,96) 的 wind/rain。
   选项：ERA5 重采样（原 `utils/download-data/wind/wind_data_era5.py` 已删，需确认新数据源），
   或把合成数据生成器切到 macro 网格作为占位消融。
2. **N_total 校准**：潮汐模型默认 `N_total_pop=50000 / N_total_veh=15000`（合成量级）；
   真实研究区应校准为 **人口 ≈ 518,221**（base_pop_2d 合计），车辆可用 travel pt_drive 标定。
   不改的话 rho 绝对量级偏小一个数量级（影响 fatality 后果项）。
3. **网格物理尺度**：macro 标称 5000×5000m（dx=50m），但研究区 bbox 实际 4770×4830m，
   线性映射带来 ~5% 各向异性；S_cell=2500m² vs 实际 ~2304m²（-8%）。
   建议：要么把 bbox 外扩/重采样到正 5km，要么把 dx/dy 改为 47.7/48.3 并同步 S_cell。
4. **travel 时段 → NT=96 映射**：信令是 10 个时段切片（模式占比随时段变化，
   pt_drive 27%→75%），需插值/分段拟合到 96 个 15min 步，用于校准
   `traffic_activation`/`population_activation` 时间曲线（当前是高斯形状的经验曲线）。

## 5. 结论

**适合。** 数据类型、形状、语义编码、坐标/网格约定与 `src` 的契约完全对齐，
真实管线已端到端跑通；POI/travel 的采样稀疏属于"绝对量级校准问题"而非"不兼容"。
补齐气象 + 校准 N_total 后即可跑正式的四风险张量（p_crash/fatality/property/noise）与 A* 规划实验。
