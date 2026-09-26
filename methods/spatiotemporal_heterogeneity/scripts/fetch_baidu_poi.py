#!/usr/bin/env python3
"""
百度地图 POI 抓取脚本（研究区真实 POI 数据）

研究区：methods/spatiotemporal_heterogeneity/data/01_raw/buildings_max_range
        WGS84 bbox = (113.2910928837698, 23.073499711374893,
                      113.33841698453455, 23.116852006517036)

方法：
  - 百度 place/v2/search 圆形区域检索（矩形检索 bounds 对该 AK 无权限）
  - 自适应网格：bbox 划分为 N×N 单元格，每格以「格心 + 半对角线半径」做圆形检索；
    单元格检索结果疑似被截断（>= SATURATION_THRESHOLD 条）时四分细分重抓
  - 关键词枚举：单关键词检索（类别词/具体词），避免 union 检索的 total 截断不透明问题
  - 坐标：请求 ret_coordtype=gcj02ll，本地 gcj02 -> wgs84 转换，输出 CRS84
  - 去重：uid 去重；最终裁剪到研究区 bbox
  - 断点续传：checkpoint JSON 周期性落盘，--resume 续跑

输出（默认写入 data/01_raw/poi/）：
  - poi_baidu.geojson   : 与 poi_osm.geojson 同构（Point + 属性），含 poi_class 五分类
  - poi_baidu.xlsx      : 表格版
  - poi_baidu_stats.json: 抓取统计（请求数、各关键词/类别数量、截断单元格等）

用法：
  BAIDU_MAPS_AK=<你的ak> python3 fetch_baidu_poi.py [--max-requests 3000] [--resume]

注意：AK 通过环境变量传入，切勿写入代码/仓库。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 研究区（与 buildings_max_range.geojson / poi/README.md 一致）
# ---------------------------------------------------------------------------
BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "01_raw" / "poi"
DEFAULT_CHECKPOINT = PROJECT_ROOT / "data" / "01_raw" / "poi" / ".poi_baidu_checkpoint.json"

API_URL = "https://api.map.baidu.com/place/v2/search"
# 该 AK 为浏览器端 AK，检索服务要求携带 Referer
API_HEADERS = {"Referer": "https://lbsyun.baidu.com/"}

PAGE_SIZE = 20
# 文档：单次请求 total 最多 150；实测单格（radius_limit=true）疑似 ~60 条即被截断。
# 抓取数达到该阈值即认为「可能截断」并细分单元格。
SATURATION_THRESHOLD = 55

# ---------------------------------------------------------------------------
# 关键词 -> 默认五分类（实际分类优先用返回的 tag 详细分类，见 classify_record）
# ---------------------------------------------------------------------------
# 五分类：residential / office / institution / transport / industrial
KEYWORDS: List[Tuple[str, str]] = [
    # 机构（教育/医疗/政府/公共文体）— 稀疏优先，确保预算不足时也完整
    ("学校", "institution"),
    ("幼儿园", "institution"),
    ("医院", "institution"),
    ("诊所", "institution"),
    ("政府", "institution"),
    ("派出所", "institution"),
    ("图书馆", "institution"),
    ("体育馆", "institution"),
    # 交通
    ("地铁站", "transport"),
    ("公交站", "transport"),
    ("停车场", "transport"),
    ("加油站", "transport"),
    ("充电站", "transport"),
    ("汽车站", "transport"),
    # 工业
    ("工厂", "industrial"),
    ("工业园", "industrial"),
    ("物流园", "industrial"),
    # 住宅
    ("住宅小区", "residential"),
    ("公寓", "residential"),
    ("别墅", "residential"),
    ("楼盘", "residential"),
    # 办公/商业（poi_parser.classify_poi 将商业服务业归入 office）— 高密度放最后
    ("写字楼", "office"),
    ("银行", "office"),
    ("酒店", "office"),
    ("宾馆", "office"),
    ("商场", "office"),
    ("超市", "office"),
    ("咖啡厅", "office"),
    ("便利店", "office"),
    ("餐厅", "office"),
    ("公司", "office"),
]

# tag 一级分类 -> 五分类（tag 形如 "房地产;住宅区"、"公司企业;工厂"）
TAG_CLASS = {
    "房地产": "residential",
    "公司企业": "office",
    "餐饮": "office",
    "购物": "office",
    "生活服务": "office",
    "体育休闲": "office",
    "金融": "office",
    "酒店": "office",
    "住宿服务": "office",
    "教育培训": "institution",
    "医疗": "institution",
    "政府机构": "institution",
    "公共设施": "institution",
    "文化场馆": "institution",
    "交通设施": "transport",
    "道路附属": "transport",
}

# 名称/标签关键字覆盖规则（按优先级从上到下匹配，解决 "房地产;商务写字楼"、"公司企业;工厂"、
# "花园酒店" 等易混情况：先工业/交通/机构，再商业办公，最后住宅）
NAME_TAG_RULES: List[Tuple[Tuple[str, ...], str]] = [
    (("工厂", "工业园", "工业", "产业园", "物流", "仓库", "仓储"), "industrial"),
    (("地铁", "公交", "车站", "客运", "停车", "加油", "充电", "机场", "码头"), "transport"),
    (("幼儿园", "学校", "学院", "大学", "中学", "小学", "培训"), "institution"),
    (("医院", "卫生", "诊所", "门诊", "急救"), "institution"),
    (("图书馆", "文化馆", "科技馆", "博物馆", "美术馆", "体育馆", "体育中心"), "institution"),
    (("写字楼", "商务楼", "大厦", "酒店", "宾馆", "商场", "购物中心", "超市", "便利店",
      "餐厅", "饭店", "银行", "咖啡", "公司"), "office"),
    (("小区", "花园", "苑", "公寓", "新村", "住宅", "别墅", "山庄"), "residential"),
]


# ---------------------------------------------------------------------------
# 坐标转换 gcj02 -> wgs84
# ---------------------------------------------------------------------------
def _gcj02_offset(lat: float, lng: float) -> Tuple[float, float]:
    a = 6378245.0
    ee = 0.00669342162296594323
    d_lat = _transform_lat(lng - 105.0, lat - 35.0)
    d_lng = _transform_lng(lng - 105.0, lat - 35.0)
    rad_lat = math.radians(lat)
    magic = math.sin(rad_lat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    d_lat = (d_lat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * math.pi)
    d_lng = (d_lng * 180.0) / (a / sqrt_magic * math.cos(rad_lat) * math.pi)
    return d_lat, d_lng


def _transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320.0 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def _transform_lng(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def gcj02_to_wgs84(lat: float, lng: float) -> Tuple[float, float]:
    """迭代求解 gcj02 -> wgs84（精度 ~1m 内）"""
    w_lat, w_lng = lat, lng
    for _ in range(6):
        d_lat, d_lng = _gcj02_offset(w_lat, w_lng)
        n_lat, n_lng = lat - d_lat, lng - d_lng
        if abs(n_lat - w_lat) < 1e-8 and abs(n_lng - w_lng) < 1e-8:
            w_lat, w_lng = n_lat, n_lng
            break
        w_lat, w_lng = n_lat, n_lng
    return w_lat, w_lng


# ---------------------------------------------------------------------------
# 分类
# ---------------------------------------------------------------------------
def classify_record(name: str, tag: str, default_class: str) -> str:
    """百度 POI -> 五分类。优先级：名称/标签规则 > tag 一级分类 > 关键词默认类。"""
    text = f"{name};{tag}"
    for keys, cls in NAME_TAG_RULES:
        if any(k in text for k in keys):
            return cls
    first = (tag or "").split(";")[0].strip()
    if first in TAG_CLASS:
        return TAG_CLASS[first]
    return default_class


# ---------------------------------------------------------------------------
# API 调用
# ---------------------------------------------------------------------------
class BaiduClient:
    def __init__(self, ak: str, sleep: float = 0.35, max_requests: int = 3000):
        self.ak = ak
        self.sleep = sleep
        self.max_requests = max_requests
        self.n_requests = 0
        self.quota_exhausted = False

    def search_circle(self, query: str, lat: float, lng: float, radius: float, page_num: int) -> dict:
        if self.n_requests >= self.max_requests:
            self.quota_exhausted = True  # 借用标志位表示预算耗尽
            return {"status": -2, "message": "request budget exhausted", "results": []}
        params = {
            "ak": self.ak,
            "query": query,
            "location": f"{lat:.6f},{lng:.6f}",
            "radius": str(int(radius)),
            "radius_limit": "true",
            "coord_type": "1",           # 输入中心点为 WGS84
            "ret_coordtype": "gcj02ll",  # 输出 GCJ02，本地转 WGS84
            "scope": "2",                # 含 detail_info.tag
            "page_size": str(PAGE_SIZE),
            "page_num": str(page_num),
            "output": "json",
        }
        url = API_URL + "?" + urllib.parse.urlencode(params)
        for attempt in range(5):
            self.n_requests += 1
            try:
                req = urllib.request.Request(url, headers=API_HEADERS)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.load(resp)
                status = data.get("status")
                if status == 0:
                    time.sleep(self.sleep)
                    return data
                if status in (4, 302):  # 4=配额校验失败；302=限流/配额受限（实测退避后可恢复）
                    wait = 60 * (attempt + 1)
                    print(
                        f"  [限流] status={status} {data.get('message')}，退避 {wait}s 重试 {attempt + 1}/5",
                        flush=True,
                    )
                    if attempt >= 4:
                        self.quota_exhausted = True
                        return data
                    time.sleep(wait)
                    continue
                if status == 9:
                    self.quota_exhausted = True
                    return data
                time.sleep(0.5)
                return data
            except Exception as exc:  # 网络抖动
                if attempt == 4:
                    print(f"  [网络失败] {exc}", flush=True)
                    return {"status": -1, "message": str(exc), "results": []}
                time.sleep(1.5 * (attempt + 1))
        return {"status": -1, "message": "unknown", "results": []}


# ---------------------------------------------------------------------------
# 抓取主流程
# ---------------------------------------------------------------------------
def record_from_result(res: dict, keyword: str, default_class: str) -> Optional[dict]:
    loc = res.get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    wgs_lat, wgs_lng = gcj02_to_wgs84(float(lat), float(lng))
    di = res.get("detail_info") or {}
    name = res.get("name") or ""
    tag = di.get("tag") or ""
    cls = classify_record(name, tag, default_class)
    return {
        "uid": res.get("uid", ""),
        "name": name,
        "class": cls,
        "keyword": keyword,
        "tag": tag,
        "baidu_type": di.get("type", ""),
        "address": res.get("address", ""),
        "province": res.get("province", ""),
        "city": res.get("city", ""),
        "area": res.get("area", ""),
        "telephone": res.get("telephone", ""),
        "detail_url": di.get("detail_url", ""),
        "lng_bd09": float(loc.get("lng")),
        "lat_bd09": float(loc.get("lat")),
        "lng_wgs84": round(wgs_lng, 7),
        "lat_wgs84": round(wgs_lat, 7),
    }


def crawl(
    client: BaiduClient,
    out_dir: Path,
    checkpoint_path: Path,
    base_grid: int,
    max_depth: int,
    resume: bool,
) -> Dict[str, dict]:
    minx, miny, maxx, maxy = BBOX
    records: Dict[str, dict] = {}
    truncated_cells: List[dict] = []

    if resume and checkpoint_path.exists():
        ck = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        records = ck.get("records", {})
        client.n_requests = ck.get("n_requests", 0)
        print(f"[resume] 已加载 {len(records)} 条记录，已用请求数 {client.n_requests}")

    def save_checkpoint():
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps({"records": records, "n_requests": client.n_requests}, ensure_ascii=False),
            encoding="utf-8",
        )

    def fetch_cell(
        keyword: str,
        default_class: str,
        cx: float,
        cy: float,
        cw: float,
        ch: float,
        depth: int,
    ):
        """抓取一个 (关键词, 单元格)；疑似截断且未到最大深度时四分细分。

        cw/ch 为单元格宽高（度），圆形检索半径取单元格半对角线以完全覆盖。
        """
        if client.quota_exhausted:
            return
        radius = math.hypot(cw, ch) / 2.0
        page, got = 0, 0
        while True:
            data = client.search_circle(keyword, cx, cy, radius, page)
            if data.get("status") != 0:
                print(f"  [跳过] {keyword} cell=({cx:.5f},{cy:.5f}) status={data.get('status')} {data.get('message')}")
                return
            results = data.get("results") or []
            for res in results:
                rec = record_from_result(res, keyword, default_class)
                if rec is None:
                    continue
                # 裁剪到研究区 bbox（radius_limit=true 仍有少量越界）
                if not (minx <= rec["lng_wgs84"] <= maxx and miny <= rec["lat_wgs84"] <= maxy):
                    continue
                records.setdefault(rec["uid"], rec)
            got += len(results)
            if len(results) < PAGE_SIZE:
                break
            page += 1
            if page >= 6:  # 单元格最多 120 条，超过即交给细分处理
                break

        saturated = got >= SATURATION_THRESHOLD or page >= 6
        if saturated and depth < max_depth:
            hw, hh = cw / 2.0, ch / 2.0
            for dx in (-1, 1):
                for dy in (-1, 1):
                    fetch_cell(
                        keyword,
                        default_class,
                        cx + dx * hw / 2.0,
                        cy + dy * hh / 2.0,
                        hw,
                        hh,
                        depth + 1,
                    )
        elif saturated:
            truncated_cells.append(
                {"keyword": keyword, "lng": round(cx, 6), "lat": round(cy, 6),
                 "radius": int(radius), "got": got}
            )

    # 基础网格
    cell_w = (maxx - minx) / base_grid
    cell_h = (maxy - miny) / base_grid

    total_pairs = len(KEYWORDS) * base_grid * base_grid
    done_pairs = 0
    for keyword, default_class in KEYWORDS:
        before_n = client.n_requests
        before_poi = len(records)
        for i in range(base_grid):
            for j in range(base_grid):
                if client.quota_exhausted:
                    break
                cx = minx + (i + 0.5) * cell_w
                cy = miny + (j + 0.5) * cell_h
                fetch_cell(keyword, default_class, cx, cy, cell_w, cell_h, 0)
                done_pairs += 1
                if done_pairs % 50 == 0:
                    save_checkpoint()
        print(
            f"[{keyword}] +{len(records) - before_poi} 条（累计 {len(records)}），"
            f"本关键词请求 {client.n_requests - before_n} 次（累计 {client.n_requests}）",
            flush=True,
        )
        save_checkpoint()
        if client.quota_exhausted:
            print("[停止] 请求预算/配额耗尽，保存现有结果。")
            break

    save_checkpoint()
    stats = {
        "requests_used": client.n_requests,
        "poi_total": len(records),
        "truncated_cells": truncated_cells,
    }
    (out_dir / "poi_baidu_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return records


def write_outputs(records: Dict[str, dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    features = []
    for rec in sorted(records.values(), key=lambda r: (r["class"], r["name"])):
        props = dict(rec)
        lng = props.pop("lng_wgs84")
        lat = props.pop("lat_wgs84")
        # 与 poi_osm.geojson 同构字段 + 百度原始字段
        props["poi_class"] = props.pop("class")
        props["category_hint"] = props["poi_class"]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lng, lat]},
                "properties": props,
            }
        )

    geojson = {
        "type": "FeatureCollection",
        "name": "poi_baidu",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    gj_path = out_dir / "poi_baidu.geojson"
    gj_path.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    try:
        import pandas as pd

        rows = [
            {
                "name": r["name"],
                "class": r["class"],
                "lng_wgs84": r["lng_wgs84"],
                "lat_wgs84": r["lat_wgs84"],
                "lng_bd09": r["lng_bd09"],
                "lat_bd09": r["lat_bd09"],
                "tag": r["tag"],
                "baidu_type": r["baidu_type"],
                "address": r["address"],
                "area": r["area"],
                "telephone": r["telephone"],
                "uid": r["uid"],
                "keyword": r["keyword"],
                "detail_url": r["detail_url"],
            }
            for r in records.values()
        ]
        df = pd.DataFrame(rows).sort_values(["class", "name"])
        df.to_excel(out_dir / "poi_baidu.xlsx", index=False)
    except Exception as exc:
        print(f"[警告] xlsx 写出失败：{exc}")

    # 统计
    by_class: Dict[str, int] = {}
    for r in records.values():
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    print("分类统计:", json.dumps(by_class, ensure_ascii=False))
    print(f"共 {len(records)} 条 POI -> {gj_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="百度地图 POI 抓取（研究区）")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    ap.add_argument("--base-grid", type=int, default=4, help="基础网格 N×N")
    ap.add_argument("--max-depth", type=int, default=2, help="截断单元格最大细分深度")
    ap.add_argument("--max-requests", type=int, default=3000)
    ap.add_argument("--sleep", type=float, default=0.35)
    ap.add_argument("--resume", action="store_true", help="从 checkpoint 续跑")
    args = ap.parse_args()

    ak = os.environ.get("BAIDU_MAPS_AK", "").strip()
    if not ak:
        print("错误：请通过环境变量 BAIDU_MAPS_AK 传入百度地图 AK", file=sys.stderr)
        sys.exit(2)

    out_dir = Path(args.out_dir)
    client = BaiduClient(ak, sleep=args.sleep, max_requests=args.max_requests)
    records = crawl(
        client,
        out_dir,
        Path(args.checkpoint),
        base_grid=args.base_grid,
        max_depth=args.max_depth,
        resume=args.resume,
    )
    if records:
        write_outputs(records, out_dir)


if __name__ == "__main__":
    main()
