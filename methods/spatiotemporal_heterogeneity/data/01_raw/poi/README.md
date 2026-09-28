# POI 原始数据说明

## `poi_baidu.geojson` / `poi_baidu.xlsx`（**唯一分析口径**，2026-09-27 冻结）

- **来源**：百度地图 Agent Plan 语义检索（31 关键词 × 6×5 网格 930 格点，uid 去重）
- **数量**：**2,834 条**（residential 316 / office 1,444 / institution 561 / transport 492 / industrial 21）
- **坐标系**：WGS84（CRS84），原始 gcj02 保留在 `lng_gcj02`/`lat_gcj02` 字段
- **分类**：属性 `poi_class` 为五分类结果，`poi_parser.classify_poi` 优先识别该字段
- **处理链**：`scripts/fetch_baidu_poi_agentplan.py`（抓取，`fetch_baidu_poi.py` 提供分类/坐标工具）
  → `scripts/merge_poi_sources.py`（合并去重）→ 本文件 → `../../02_processed/poi_counts.npz`
- **已知偏差**：接口单次上限 10 条 × 格心最近邻取样 → 高密度类被压平，**相对密度格局可用、
  绝对计数偏低**（详见 `../../docs/POI_TASK_REPORT_20260926.md` §4）

## 历史版本（已移除，git 历史可查）

按「仅保留当前项目版本」原则（2026-09-28），以下旧版已从 HEAD 移除：

- `poi_osm.geojson/.xlsx`（1,898，OSM 占位/对照）
- `poi_baidu_agentplan.geojson/.xlsx/_stats.json`（抓取中间产物，与最终版内容重复）
- `01_raw/poi.geojson`（21,082，合成+OSM 冻结集，与 poi_counts 口径不一致）
- `02_processed/poi_counts_osm.npz`（旧 OSM 计数）

`landuse_map_b/c.npy` 交叉验证存档不受影响（见 `../../docs/DATA_METHOD_FIT_20260927.md`）。
