# POI 原始数据说明

## `poi_baidu.geojson` / `poi_baidu.xlsx`（正式数据，2026-09-26）

- **来源**：百度地图（Agent Plan 语义检索为主，place/v2 检索补充），多源合并、uid 去重
- **数量**：2168 条（residential 311 / office 693 / institution 571 / transport 554 / industrial 39）
- **坐标系**：WGS84（CRS84），原始 gcj02 坐标保留在 `lng_gcj02`/`lat_gcj02` 字段
- **分类**：属性 `poi_class` 为五分类结果，`poi_parser.classify_poi` 优先识别该字段
- **抓取脚本**：`scripts/fetch_baidu_poi_agentplan.py`（主）+ `scripts/fetch_baidu_poi.py`（补）
  + `scripts/merge_poi_sources.py`（合并 → `poi_baidu.geojson` + `../../02_processed/poi_counts.npz`）
- 详细文档：[`../docs/POI_TASK_REPORT_20260926.md`](../docs/POI_TASK_REPORT_20260926.md)

## `poi_osm.geojson` / `poi_osm.xlsx`（占位/对照）

- **来源**：OpenStreetMap（Overpass API），ODbL 许可
- **范围**：研究区 `buildings_max_range`（113.2911–113.3384E，23.0735–23.1169N，约 23.28 km²，广州天河/珠江新城）
- **坐标系**：WGS84（CRS84）
- **获取时间**：2026-09-26
- **数量**：1947 条（residential 764 / office 344 / institution 99 / transport 723 / industrial 17）

### ⚠️ 这是占位数据

OSM 在中国大陆覆盖稀疏，同范围高德地图预计可获取 1–3 万条 POI（约为本数据的 10 倍），
且口径不同：OSM `residential` 是住宅**建筑面**中心点，高德「住宅小区」是小区级 POI。

**本数据只适合管线联调与可视化调试，正式分析请使用高德 POI 数据。**

### 字段

- 保留了全部 OSM 原始 tags（`building` / `amenity` / `shop` / `office` / `landuse` / `railway` ...），
  这是 `poi_parser.classify_poi` 分类所依赖的字段，**不要删掉**
- `category_hint`：预分类结果（与 `classify_poi` 口径一致），供人工核对
- `osm_id` / `name` / `type` / `address`：便于查看的汇总字段

### 已知问题

- 49 条（2.5%）要素中心点落在研究区外（跨边界建筑的中心点），传 `city_bounds` 时会被自动丢弃
- 33.2% 无名称（住宅建筑、公交站为主）
- 生成方式：`.openclaw/tmp/osm_poi_fetch.py`（Overpass 抓取）→ `.openclaw/tmp/osm_to_geojson.py`（分类转 GeoJSON）

## `../../02_processed/poi_counts_osm.npz`

由 `poi_parser.parse_osm_poi_geojson` 生成的五类 POI 计数栅格（100×100），
`city_bounds=(113.2911, 23.0735, 113.3384, 23.1169)`。

文件名带 `_osm` 后缀是为了**避免与正式的 `poi_counts.npz` 混淆**；高德数据到位后请重新生成并覆盖正式文件。

```python
from data_provision.poi_parser import parse_osm_poi_geojson
BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)
parse_osm_poi_geojson("data/01_raw/poi/poi_osm.geojson", city_bounds=BBOX, save=True)
```
