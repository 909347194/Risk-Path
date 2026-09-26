#!/usr/bin/env python3
"""
合并多来源百度 POI 抓取结果 -> 最终交付数据 + 栅格计数。

来源（按 uid 去重，agentplan 优先）：
  1. data/01_raw/poi/poi_baidu_agentplan.geojson   （Agent Plan 语义检索，主源）
  2. data/01_raw/poi/v2/poi_baidu.geojson          （place/v2 周边检索，补充，可缺省）

产出：
  - data/01_raw/poi/poi_baidu.geojson / poi_baidu.xlsx   （最终 POI 数据，CRS84）
  - data/02_processed/poi_counts.npz                    （五分类计数栅格 100×100，poi_parser 口径）
  - data/01_raw/poi/poi_baidu_merge_stats.json          （合并统计）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

POI_DIR = PROJECT_ROOT / "data" / "01_raw" / "poi"
SOURCES = [POI_DIR / "poi_baidu_agentplan.geojson", POI_DIR / "v2" / "poi_baidu.geojson"]
OUT_GEOJSON = POI_DIR / "poi_baidu.geojson"
OUT_XLSX = POI_DIR / "poi_baidu.xlsx"
BBOX = (113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036)


def load_source(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for feat in data.get("features", []):
        props = dict(feat.get("properties") or {})
        coords = (feat.get("geometry") or {}).get("coordinates") or [None, None]
        uid = props.get("uid") or f"nouid-{props.get('name')}-{coords[0]}-{coords[1]}"
        props["lng_wgs84"] = coords[0]
        props["lat_wgs84"] = coords[1]
        out[uid] = props
    return out


def main() -> None:
    merged: dict = {}
    source_counts = {}
    for src in SOURCES:
        recs = load_source(src)
        source_counts[src.name] = len(recs)
        for uid, props in recs.items():
            merged.setdefault(uid, props)  # agentplan 优先（排在前面）

    minx, miny, maxx, maxy = BBOX
    merged = {
        uid: p
        for uid, p in merged.items()
        if p.get("lng_wgs84") is not None
        and minx <= p["lng_wgs84"] <= maxx
        and miny <= p["lat_wgs84"] <= maxy
    }

    features = []
    for uid, props in sorted(merged.items(), key=lambda kv: (kv[1].get("poi_class", ""), kv[1].get("name", ""))):
        p = dict(props)
        lng = p.pop("lng_wgs84")
        lat = p.pop("lat_wgs84")
        features.append(
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lng, lat]}, "properties": p}
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "poi_baidu",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    OUT_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")

    by_class: dict = {}
    for p in merged.values():
        c = p.get("poi_class", "unknown")
        by_class[c] = by_class.get(c, 0) + 1

    # 五分类计数栅格（poi_parser 口径：识别 poi_class 显式字段）
    try:
        from data_provision.poi_parser import parse_osm_poi_geojson

        counts = parse_osm_poi_geojson(OUT_GEOJSON, city_bounds=BBOX, save=True)
        npz_total = {k: float(v.sum()) for k, v in counts.items()}
    except Exception as exc:
        npz_total = {"error": str(exc)}
        print(f"[警告] poi_counts 生成失败：{exc}")

    try:
        import pandas as pd

        rows = [
            {
                "name": p.get("name"),
                "class": p.get("poi_class"),
                "lng_wgs84": p.get("lng_wgs84") if "lng_wgs84" in p else None,
                "lat_wgs84": p.get("lat_wgs84") if "lat_wgs84" in p else None,
                "tag": p.get("tag"),
                "address": p.get("address"),
                "area": p.get("area"),
                "telephone": p.get("telephone"),
                "uid": uid,
                "keyword": p.get("keyword"),
            }
            for uid, p in merged.items()
        ]
        df = pd.DataFrame(rows)
        # 重新挂回坐标（上面 pop 了）
        coords = {f["properties"].get("uid"): f["geometry"]["coordinates"] for f in features}
        df["lng_wgs84"] = df["uid"].map(lambda u: coords.get(u, [None, None])[0])
        df["lat_wgs84"] = df["uid"].map(lambda u: coords.get(u, [None, None])[1])
        df.sort_values(["class", "name"]).to_excel(OUT_XLSX, index=False)
    except Exception as exc:
        print(f"[警告] xlsx 写出失败：{exc}")

    stats = {"sources": source_counts, "merged_total": len(merged), "by_class": by_class, "npz": npz_total}
    (POI_DIR / "poi_baidu_merge_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
