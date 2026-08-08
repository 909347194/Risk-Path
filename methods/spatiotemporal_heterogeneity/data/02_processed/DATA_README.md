# 02_processed 数据说明文档

> 数据来源：[chenchs0629/GBA-UBF](https://github.com/chenchs0629/GBA-UBF)  
> 覆盖区域：粤港澳大湾区（Greater Bay Area）  
> 数据日期：2020-10-22（周四）

---

## 目录结构

```
02_processed/
├── Travel/Guangzhou/          # ✅ 可直接使用（CSV）
│   ├── gz_user_counts_risk_analysis_20201022_all.csv    # 全时段汇总
│   ├── gz_user_counts_risk_analysis_20201022_0.csv      # 时段 0
│   ├── gz_user_counts_risk_analysis_20201022_1.csv      # 时段 1
│   ├── ...
│   └── gz_user_counts_risk_analysis_20201022_9.csv      # 时段 9
│
├── Building/Guangzhou_WGS84/  # ⚠️ 需 Git LFS 拉取（Shapefile）
│   ├── Guangzhou_WGS84.shp    #   建筑轮廓（141 MB）
│   ├── Guangzhou_WGS84.dbf    #   属性表
│   ├── Guangzhou_WGS84.shx    #   空间索引
│   ├── Guangzhou_WGS84.prj    #   坐标系定义
│   ├── Guangzhou_WGS84.cpg    #   编码页
│   ├── Guangzhou_WGS84.sbn    #   空间索引
│   ├── Guangzhou_WGS84.sbx    #   空间索引
│   └── Guangzhou_WGS84.shp.xml #  元数据
│
├── Guangzhou/                 # ⚠️ 需 Git LFS 拉取（Pickle）
│   ├── CsvNum_all_WithBuilding_True.pkl                        # 254 MB
│   └── CsvNum_all_WithBuilding_True_Fatality_0.7_Property_0.2_Noise_0.1.pkl
│
└── synthetic/                 # 合成数据（已就绪）
    ├── base_pop_2d.npy
    ├── building_heights.npy
    ├── landuse_map.npy
    ├── poi_counts.npz
    ├── road_mask.npy
    ├── od_pairs.json
    └── metadata.json
```

---

## 1. Travel 出行数据

### 概述

基于手机信令数据提取的粤港澳大湾区出行记录，按出行模式和时段聚合到规则网格。

### 文件格式

每个 CSV 文件包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `grid_id` | int64 | 网格唯一标识符 |
| `mode` | str | 出行模式 |
| `user_counts` | int | 该网格内的出行用户数 |
| `lat_min` | float | 网格南边界纬度（°） |
| `lat_max` | float | 网格北边界纬度（°） |
| `lon_min` | float | 网格西边界经度（°） |
| `lon_max` | float | 网格东边界经度（°） |
| `clat` | float | 网格中心纬度（°） |
| `clon` | float | 网格中心经度（°） |

> 注：`_all.csv` 仅含 `grid_id, mode, user_counts`，不含坐标列。

### 出行模式

| 模式 | 占比 | 说明 |
|------|------|------|
| `pt_drive` | ~60% | 驾车/网约车（可用于车辆密度 ρ_veh） |
| `bike` | ~34% | 骑行（共享单车/电动车） |
| `walking` | ~6% | 步行 |
| `subway` | <0.1% | 地铁（记录较少） |

### 网格参数

| 参数 | 值 |
|------|---|
| 网格分辨率 | 0.0001° × 0.0001°（≈ **11m × 10m**） |
| 唯一网格数 | 53,558 |
| 纬度范围 | 20.25°N ~ 25.47°N |
| 经度范围 | 110.00°E ~ 117.05°E |
| 覆盖区域 | 粤港澳大湾区全域 |

### 时段统计

现有 10 个时段文件（`_0.csv` ~ `_9.csv`），对应数据如下：

| 时段 | 总用户数 | 活跃网格数 | 平均/网格 | pt_drive% | bike% |
|------|---------|-----------|----------|----------|-------|
| 0 | 2,589,439 | 25,474 | 50.5 | 27.6% | 69.7% |
| 1 | 2,300,823 | 27,223 | 48.4 | 33.2% | 66.2% |
| 2 | 2,011,168 | 26,467 | 45.8 | 36.8% | 62.9% |
| 3 | 1,724,573 | 26,400 | 40.5 | 42.0% | 57.7% |
| 4 | 1,435,793 | 27,009 | 34.0 | 48.3% | 51.5% |
| 5 | 1,226,925 | 28,773 | 28.4 | 55.7% | 44.1% |
| 6 | 1,059,703 | 30,361 | 24.2 | 62.8% | 37.1% |
| 7 | 940,317 | 32,235 | 21.1 | 68.0% | 31.9% |
| 8 | 810,041 | 33,134 | 18.3 | 72.5% | 27.4% |
| 9 | 630,904 | 31,273 | 15.6 | 75.1% | 24.8% |

**关键发现**：
- 总用户从时段 0（259 万）递减至时段 9（63 万），呈凌晨→上午衰减趋势
- 模式迁移显著：凌晨 `bike` 占 70%，上午 `pt_drive` 占 75%
- 活跃网格数随时间增加（凌晨集中，白天扩散）

### 与本项目的映射关系

| 本项目概念 | Travel 数据映射 | 说明 |
|-----------|----------------|------|
| ρ_pop(x,y,t) | 所有模式 `user_counts` 按网格聚合 | 动态人口密度 |
| ρ_veh(x,y,t) | `mode == 'pt_drive'` 的 `user_counts` | 车辆出行密度 |
| POI 热力 | 高 `user_counts` 网格的空间聚集 | 可反推 POI 权重 |
| 潮汐验证 | 时段间 `user_counts` 变化 | 验证 Partition of Unity |

### 裁剪到广州中心区

```python
import pandas as pd

df = pd.read_csv('Travel/Guangzhou/gz_user_counts_risk_analysis_20201022_8.csv')
guangzhou = df[
    (df['clat'] > 23.0) & (df['clat'] < 23.3) &
    (df['clon'] > 113.1) & (df['clon'] < 113.4)
]
```

广州中心区约 13,575 个网格，占总用户的 60%+。

---

## 2. Building 建筑数据

### 概述

广州市建筑轮廓矢量数据（WGS84 坐标系）。

### 文件信息

| 属性 | 值 |
|------|---|
| 格式 | ESRI Shapefile |
| 坐标系 | WGS84（EPSG:4326） |
| 几何类型 | Polygon（建筑轮廓） |
| 文件大小 | 141 MB（LFS） |
| 状态 | ⚠️ **需 `git lfs pull` 拉取** |

### 利用方式

拉取后可用于：
- 提取建筑高度 → `building_heights` 矩阵
- 计算建筑密度 → 障碍物掩码 `obstacle`
- 城市峡谷效应 → SVF（天空可视因子）计算
- 财产风险 → `E_property` 张量

### 拉取方法

```bash
git lfs pull
```

---

## 3. Guangzhou 风险分析数据

### 概述

预计算的广州市风险分析结果，含建筑信息。

### 文件信息

| 文件 | 大小 | 说明 |
|------|------|------|
| `CsvNum_all_WithBuilding_True.pkl` | 254 MB | 含建筑信息的风险分析结果 |
| `CsvNum_all_WithBuilding_True_Fatality_0.7_Property_0.2_Noise_0.1.pkl` | — | 指定权重组合的结果 |
| 状态 | ⚠️ **需 `git lfs pull` 拉取** |

### 利用方式

拉取后可用于：
- 作为 benchmark 对比本模型输出
- 验证风险张量计算的正确性
- 参考其权重预设（Fatality=0.7, Property=0.2, Noise=0.1）

---

## Git LFS 拉取说明

Building 和 Guangzhou 目录下的大文件使用 Git LFS 存储。当前仓库中的文件为 LFS 指针（~130 bytes），需执行以下命令拉取实际数据：

```bash
# 安装 Git LFS（如未安装）
git lfs install

# 拉取所有 LFS 文件
git lfs pull

# 或仅拉取特定目录
git lfs pull --include="methods/spatiotemporal_heterogeneity/data/02_processed/Building/**"
git lfs pull --include="methods/spatiotemporal_heterogeneity/data/02_processed/Guangzhou/**"
```

---

## 合成数据（synthetic/）

由 `utils/synthetic_data_factory` 生成的合成城市场景数据，用于微观实验验证。

| 文件 | 形状 | 说明 |
|------|------|------|
| `base_pop_2d.npy` | (nx, ny) | 静态基础人口密度 |
| `building_heights.npy` | (ny, nx) | 建筑高度（层） |
| `landuse_map.npy` | (ny, nx) | 土地利用编码（1~6） |
| `poi_counts.npz` | 5×(nx, ny) | POI 计数栅格（5 类） |
| `road_mask.npy` | (ny, nx) | 道路掩码 |
| `od_pairs.json` | — | 起终点对 |
| `metadata.json` | — | 生成参数元数据 |

土地利用编码：`1=住宅, 2=商业, 3=机构, 4=工业, 5=道路, 6=绿地/水域`

---

*最后更新：2026-08-08*
