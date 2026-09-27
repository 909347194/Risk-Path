# POI 数据获取任务报告（2026-09-26）

> 给第二天接手的自己/协作者：本报告记录本次 POI 数据获取的完整状态、已知约束、未完事项与复现命令。

## 1. 任务目标

为 `methods/spatiotemporal_heterogeneity` 研究区获取**真实 POI 数据**，替换占位的 OSM 数据
（`data/01_raw/poi/poi_osm.*`，1947 条，仅适合管线联调）。

- 研究区：`data/01_raw/buildings_max_range`
- WGS84 bbox：`(113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)`
- 约 23.3 km²，广州珠江新城/猎德—广州塔一带
- 五分类口径（与 `poi_parser.classify_poi` 一致）：
  `residential / office / institution / transport / industrial`

## 2. 当前数据状态（截至 2026-09-27 14:00，**抓取已全部完成**）

| 数据集 | 文件 | 数量 | 说明 |
|---|---|---|---|
| 最终 POI | `data/01_raw/poi/poi_baidu.geojson` / `.xlsx` | **2834** | 多源合并、uid 去重、裁剪进 bbox、WGS84 |
| Agent Plan 源 | `data/01_raw/poi/poi_baidu_agentplan.geojson` / `.xlsx` | 2834 | 主源，31 关键词 × 6×5 网格 930 格点已全部跑完 |
| place/v2 源 | `data/01_raw/poi/v2/poi_baidu.geojson` | 0 | 日配额持续 302 未贡献（仅补充源，不影响交付） |
| 计数栅格 | `data/02_processed/poi_counts.npz` | 100×100×5 | 由 `poi_parser.parse_osm_poi_geojson` 生成 |
| OSM 占位 | `data/01_raw/poi/poi_osm.geojson` | 1947 | 保留作对照 |

五分类统计（`poi_baidu_merge_stats.json`）：
**residential 314 / office 1343 / institution 575 / transport 562 / industrial 40**

## 3. 已完成事项

1. **SSH**：生成 ed25519 密钥并注册到 GitHub（key id 164514552），SSH 方式克隆/推送本仓库。
2. **抓取脚本**（`scripts/`）：
   - `fetch_baidu_poi.py`：place/v2/search 圆形检索 + 自适应网格细分 + 断点续传 + gcj02→wgs84。
   - `fetch_baidu_poi_agentplan.py`：Agent Plan `/agent_plan/v1/place` 语义检索，网格中心×关键词枚举，
     格点级断点续传（`done_pairs`），uid 去重、bbox 裁剪、五分类。
   - `merge_poi_sources.py`：合并各源 → 最终 `poi_baidu.geojson/.xlsx` + `poi_counts.npz` + 合并统计。
3. **`poi_parser.classify_poi` 增强**：识别显式 `poi_class` 字段（百度数据用），OSM 标签规则行为不变。
4. **baidu-ai-map skill**：已安装 v1.0.9 至 `~/.openclaw/skills/`，`BAIDU_MAP_AUTH_TOKEN` 已持久化
   （`~/.profile` / `~/.bashrc`，官方 gateway env 为平台保护路径不可写，走用户预授权回退）。

## 4. 已知约束（踩过的坑，勿重复踩）

1. **place/v2（传统 AK）**：
   - 矩形检索 `bounds` 无权限（status 9）；浏览器端 AK 必须带 `Referer: https://lbsyun.baidu.com/`。
   - 日配额极小：约 140 次调用即 `status=302 天配额超限`（退避后偶发恢复，主要靠次日重置）。
   - 单次请求 `total` 上限 150；类别词检索实测 ~60-100 条即疑似截断（集合不稳定，需网格细分）。
2. **Agent Plan（`/agent_plan/v1/place`，BAIDU_MAP_AUTH_TOKEN）**：
   - 内测额度 **1000 次/5 小时**；单次最多返回 **10 条**。
   - 文字描述 bbox **无效**；`center`（gcj02，`lat,lng`）+ `sort=distance` 空间定位可靠。
   - 返回坐标为 **gcj02**，已统一转 wgs84。
3. **断点续传教训**：checkpoint 必须记「已跑格点」而不是只记请求数，否则 resume 会重复消耗配额
   （本次浪费约 200 次调用，已修复）。
4. **单位教训**：place/v2 圆形检索 `radius` 单位是**米**，脚本曾误传「度」（`int(0.008)=0`）导致一直 0 条；
   已修复为单元格宽高换算成米后取半对角线。
5. 已跑网格：`6×5` 格心 × 31 关键词 = 930 格点，每格点取「最近 10 个」（**已全部完成**）。

## 5. 任务进度（2026-09-27 14:00 更新）

- ✅ 09-27 13:40：Agent Plan 全量抓取完成（930/930 格点，最终 2834 条），已合并产出 `poi_baidu.*` + `poi_counts.npz`
- ⏳ place/v2 补抓：当日日配额持续 302 未解禁；如仍想补充，次日 00:10 后重跑：
  `BAIDU_MAPS_AK=$(cat .openclaw/tmp/baidu_ak.txt) python3 scripts/fetch_baidu_poi.py --out-dir data/01_raw/poi/v2 --checkpoint data/01_raw/poi/v2/.ckpt2.json --max-requests 1200 --max-depth 2`
  完成后 `python3 scripts/merge_poi_sources.py` 增量合并（可选，主源已够用）
- （注：09-27 00:10/02:40 两个 cron 因主会话休眠未执行，其任务已由 13:40 手动接管完成，cron 已删除）

## 6. 后续可选优化

- 提高空间覆盖：网格从 6×5 加密到 8×7（约 560 次调用/关键词，需新窗口）。
- 增加关键词（药店/面包店/公园/写字楼变体等）扩充「全部 POI」覆盖面。
- `industrial` 仅 40 条：研究区为 CBD，工业类天然稀少，可与 `landuse` 工业用地数据交叉验证。
- 高密度类别（餐厅/公司）10 条/格心是接口硬上限，密度峰值会被平滑；如需精确密度可改用
  place/v2 网格细分模式（`fetch_baidu_poi.py`，按日配额分多天跑）。
