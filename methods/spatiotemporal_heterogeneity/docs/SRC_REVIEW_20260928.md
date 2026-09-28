# src 代码审查报告（2026-09-28）

> 范围：`methods/spatiotemporal_heterogeneity/src`（data_provision / tensor_engine / algorithms）
> 方法：通读模块 + 跨矩阵实证测试 + 与 10 个新提交对账。

## 总评

**质量良好，可支撑正式实验。** 三个亮点：(1) 契约意识强——exp_data 有严格形状校验、
assembler 注释里留有"审查 HIGH 项"修复痕迹（风配置传递、噪声网格锁定两处都修对了）；
(2) 情景风/雨模型定位清醒（`is_observed:false`、"非 CFD"、"双计权约束"文档化）；
(3) 单一实现原则（build_rain 委托 tensor_engine，不再两处实现）。

## 发现清单

### 🟠 M1（中）数据处理链三足鼎立 + `run_all` 具破坏性
- 事实：`DataPipeline(data_type='real').run_all()` 会从 01_raw 重算并**覆盖** 02_processed
  已提交数据；exp_data.py 文档实测"重算 vs 提交版相对差 50%-90%"。
  当前同时存在三条处理链：`build_real_processed.py`（v2 权威）、`run_all()`（口径不同）、
  `scripts/build_landuse_map.py` 等（v1，09-27 产物）。
- 风险：任何人跑一次 run_all（教程/文档还在这样引导）即静默污染全部实验输入。
- 建议：real 模式 `run_all` 默认不落盘（或写 `_recomputed/`）；v1 脚本标注 superseded；
  DATA_PIPELINE.md 明确"唯一口径 = build_real_processed.py"。

### 🟠 M2（中）POI 数据口径不一致
- 事实：`01_raw/poi.geojson`（冻结 21,082 点，OSM tags）声称"分析用 POI 集必须冻结"，
  但 `poi_counts.npz`（实验实际消费）来自百度多源 2,834 点（`poi/poi_baidu*.geojson`），
  另有 OSM 版 1,898 点。`*poi*.geojson` glob 会同时命中 4 个文件。
- 风险：论文写"POI 21,082"而张量用 2,834 计数栅格，数据溯源对不上（审稿高危）。
- 建议：明确唯一分析口径（二选一或分层：主结果用哪个、敏感性用哪个），
  在 DATA_STATUS/POI README 写死，并把其余版本改名去掉 `poi` glob 匹配。

### 🟡 L1（低）weather_processor 成孤儿模块
- `load_wind_field/load_rain_data` 仍从 `data_provision.__init__` 导出，但已被
  `wind_environment`/`rain_environment` 取代，无调用方。建议删除或标注 deprecated。

### 🟡 L2（低）物理尺度与网格标称不一致
- bbox 4770×4830m 线性映射进 100×100（dx=dy=50m 标称 5000×5000m）：
  各向异性 ~5%，S_cell=2500m² vs 实际 ~2304m²（-8%）。影响所有"米"制参数
  （SVF 半径、峡谷距离场、巡航速度×dt 的可达距离）。
- 建议：bbox 归一或 dx/dy 用真实值；至少在 PROJECT_SPEC 注明误差界。

### 🟡 L3（低）N_total 口径未注明依据
- 实证：N_total_pop = 557,724（rho 守恒恒等 223.089×2500），而 base_pop 合计 518,221（+7.6%）；
  N_total_veh = 227,225。若为昼夜/周转放大请补注依据，否则建议对齐 WorldPop。

### 🔵 I1（提示）travel 时段→NT=96 映射未接入
- 信令 10 切片的真实模式占比曲线（pt_drive 27%→75%）可替换经验高斯 activation；
  适配报告 §4-2 跟踪。

### 🔵 I2（提示）两处可维护性小事
- `_compute_dist_to_building` 纯 Python 双扫描（100×100 无碍；网格变大可换 scipy EDT）。
- Chamfer 近似 EDT 对细长建筑有 ~3% 距离误差——对 f_obs 归一化影响可忽略。

## 已验证无问题的点（实证）

| 检查 | 结果 |
|---|---|
| 跨 6 组矩阵 y 轴对齐（正常 vs 翻转相关性） | ✅ 全部正常方向胜出（住宅×POI 0.972），无镜像错位 |
| rho 质量守恒 | ✅ 各时相总量恒等 |
| exp_data 形状校验 | ✅ (nx,ny)/(nx,ny,nt) 全覆盖，POI 逐类校验 |
| assembler 风/雨/噪声接入 | ✅ scenario 风 4D、雨缺省自动生成、噪声用调用方 grid |
| run_all(skip_weather) 签名 | ✅ 与 exp_data 调用一致 |
| NoiseConfig.from_yaml | ✅ 噪声配置真正可调（landuse_code_map 等走 common.yaml） |

## 建议处理顺序

M2（论文口径，最急）→ M1（防数据污染）→ L3/L2（写注即可）→ L1/I1/I2（顺手）。

---

## 处置结果（2026-09-28 当日执行）

| 项 | 处置 |
|---|---|
| M1 run_all 破坏性 | ✅ `DataPipeline` 增加 `allow_overwrite=False` 写回保护：real 模式重算输出改写 `02_processed/_recomputed/`（实测验证生效）；v1 处理链脚本移除，常量抽 `scripts/grid_constants.py` |
| M2 POI 口径 | ✅ 统一 `poi/poi_baidu.geojson`（2,834，与 poi_counts/Exp1 一致）为唯一分析口径；移除 poi.geojson(21,082)/poi_osm/agentplan 中间件/poi_counts_osm，README 与 DATA_STATUS 同步改写 |
| L1 weather_processor | ✅ 模块删除，`data_provision.__init__`/`pipeline.py` 导出与调用同步清理（py_compile+导入验证通过） |
| L2 物理尺度 / L3 N_total 依据 | ✅ PROJECT_SPEC 新增「数据精度注记」（误差界 + N_total 口径）；L3 的 +7.6% 依据仍建议作者确认 |
| I1 travel→activation / I2 | ⏳ 保留为后续工作 |
