#!/usr/bin/env python3
"""
百度地图 Agent Plan（baidu-ai-map skill）POI 抓取脚本

与 fetch_baidu_poi.py（place/v2/search，日配额极小）互补：
本脚本调用 Agent Plan 语义地点检索 `GET /agent_plan/v1/place`（内测约 1000 次/5h）。

实测接口行为：
  - 单次最多返回 10 条 POI（按相关性/距离排序）
  - `center` + `sort=distance` 可稳定做空间定位（center 为 gcj02，lat,lng）
  - 文字描述矩形范围（bbox）无效，因此用「网格中心 × 关键词」枚举覆盖研究区

方法：
  - 研究区 bbox（WGS84）划分为 NX×NY 个单元格，取格心（转 gcj02）作为检索中心
  - 每个关键词 × 每个格心发起一次「请列出离我最近的10个X」，按距离取近邻
  - uid 去重、裁剪到研究区 bbox、gcj02 -> wgs84 转换、五分类（复用 fetch_baidu_poi 规则）

输出（data/01_raw/poi/）：
  - poi_baidu_agentplan.geojson / .xlsx / _stats.json

用法：
  BAIDU_MAP_AUTH_TOKEN=<token> python3 fetch_baidu_poi_agentplan.py [--max-calls 980] [--resume]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_baidu_poi import (  # noqa: E402
    BBOX,
    KEYWORDS,
    _gcj02_offset,
    classify_record,
    gcj02_to_wgs84,
)

API_URL = "https://api.map.baidu.com/agent_plan/v1/place"
DEFAULT_OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "01_raw" / "poi"
DEFAULT_CHECKPOINT = DEFAULT_OUT_DIR / ".poi_baidu_agentplan_checkpoint.json"

PAGE_N = 10  # 单次调用结果上限


def wgs84_to_gcj02(lat: float, lng: float) -> Tuple[float, float]:
    d_lat, d_lng = _gcj02_offset(lat, lng)
    return lat + d_lat, lng + d_lng


class AgentPlanClient:
    def __init__(self, token: str, sleep: float = 0.25, max_calls: int = 980):
        self.token = token
        self.sleep = sleep
        self.max_calls = max_calls
        self.n_calls = 0
        self.stopped = False
        self.stop_reason = ""

    def place(self, request: str, center_gcj02: str) -> dict:
        if self.n_calls >= self.max_calls:
            self.stopped = True
            self.stop_reason = "call budget exhausted"
            return {"status": -2, "results": []}
        params = {
            "user_raw_request": request,
            "region": "广州市",
            "center": center_gcj02,
            "sort": "distance",
        }
        url = API_URL + "?" + urllib.parse.urlencode(params)
        for attempt in range(5):
            self.n_calls += 1
            try:
                req = urllib.request.Request(
                    url, headers={"Authorization": f"Bearer {self.token}"}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.load(resp)
                status = data.get("status")
                if status == 0:
                    time.sleep(self.sleep)
                    return data
                msg = str(data.get("message", ""))
                if any(k in msg for k in ("额度", "配额", "限流", "次数", "超限", "quota")):
                    self.stopped = True
                    self.stop_reason = f"quota: {msg}"
                    return data
                print(f"  [重试] status={status} {msg[:60]} {attempt + 1}/5", flush=True)
                time.sleep(5 * (attempt + 1))
            except Exception as exc:
                if attempt == 4:
                    self.stopped = True
                    self.stop_reason = f"network: {exc}"
                    return {"status": -1, "results": []}
                time.sleep(3 * (attempt + 1))
        return {"status": -1, "results": []}


def record_from_result(res: dict, keyword: str, default_class: str) -> Optional[dict]:
    loc = res.get("location") or {}
    lat, lng = loc.get("lat"), loc.get("lng")
    if lat is None or lng is None:
        return None
    wgs_lat, wgs_lng = gcj02_to_wgs84(float(lat), float(lng))
    di = res.get("detail_info") or {}
    name = res.get("name") or ""
    tag = di.get("tag") or di.get("classified_poi_tag") or ""
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
        "lng_gcj02": float(lng),
        "lat_gcj02": float(lat),
        "lng_wgs84": round(wgs_lng, 7),
        "lat_wgs84": round(wgs_lat, 7),
    }


def crawl(client: AgentPlanClient, out_dir: Path, checkpoint_path: Path, gx: int, gy: int, resume: bool) -> Dict[str, dict]:
    minx, miny, maxx, maxy = BBOX
    records: Dict[str, dict] = {}
    done_pairs: set = set()

    if resume and checkpoint_path.exists():
        ck = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        records = ck.get("records", {})
        client.n_calls = ck.get("n_calls", 0)
        done_pairs = set(ck.get("done_pairs", []))
        print(
            f"[resume] 已加载 {len(records)} 条，已用调用 {client.n_calls}，"
            f"已完成网格点 {len(done_pairs)}",
            flush=True,
        )

    def save_checkpoint():
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps(
                {
                    "records": records,
                    "n_calls": client.n_calls,
                    "done_pairs": sorted(done_pairs),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    cell_w = (maxx - minx) / gx
    cell_h = (maxy - miny) / gy
    centers: List[Tuple[float, float]] = []
    for i in range(gx):
        for j in range(gy):
            cx_wgs = minx + (i + 0.5) * cell_w
            cy_wgs = miny + (j + 0.5) * cell_h
            cy_gcj, cx_gcj = wgs84_to_gcj02(cy_wgs, cx_wgs)
            centers.append((cx_gcj, cy_gcj))

    total = len(KEYWORDS) * len(centers)
    done = 0
    for keyword, default_class in KEYWORDS:
        before = len(records)
        for cx, cy in centers:
            if client.stopped:
                break
            pair_key = f"{keyword}|{cx:.6f}|{cy:.6f}"
            if pair_key in done_pairs:
                continue
            request = f"请列出离我最近的{PAGE_N}个{keyword}"
            data = client.place(request, f"{cy:.6f},{cx:.6f}")
            for res in data.get("results") or []:
                rec = record_from_result(res, keyword, default_class)
                if rec is None:
                    continue
                if not (minx <= rec["lng_wgs84"] <= maxx and miny <= rec["lat_wgs84"] <= maxy):
                    continue
                records.setdefault(rec["uid"], rec)
            done_pairs.add(pair_key)
            done += 1
            if done % 25 == 0:
                save_checkpoint()
                print(f"  ... 进度 {done}/{total}，累计 POI {len(records)}，调用 {client.n_calls}", flush=True)
        print(f"[{keyword}] +{len(records) - before}（累计 {len(records)}，调用 {client.n_calls}）", flush=True)
        save_checkpoint()
        if client.stopped:
            print(f"[停止] {client.stop_reason}", flush=True)
            break

    save_checkpoint()
    stats = {
        "calls_used": client.n_calls,
        "poi_total": len(records),
        "stopped_reason": client.stop_reason or "completed",
        "grid": [gx, gy],
    }
    (out_dir / "poi_baidu_agentplan_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return records


def write_outputs(records: Dict[str, dict], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    features = []
    for rec in sorted(records.values(), key=lambda r: (r["class"], r["name"])):
        props = dict(rec)
        lng = props.pop("lng_wgs84")
        lat = props.pop("lat_wgs84")
        props["poi_class"] = props.pop("class")
        props["category_hint"] = props["poi_class"]
        features.append(
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [lng, lat]}, "properties": props}
        )
    geojson = {
        "type": "FeatureCollection",
        "name": "poi_baidu_agentplan",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    (out_dir / "poi_baidu_agentplan.geojson").write_text(
        json.dumps(geojson, ensure_ascii=False), encoding="utf-8"
    )
    try:
        import pandas as pd

        rows = [
            {
                "name": r["name"],
                "class": r["class"],
                "lng_wgs84": r["lng_wgs84"],
                "lat_wgs84": r["lat_wgs84"],
                "lng_gcj02": r["lng_gcj02"],
                "lat_gcj02": r["lat_gcj02"],
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
        pd.DataFrame(rows).sort_values(["class", "name"]).to_excel(
            out_dir / "poi_baidu_agentplan.xlsx", index=False
        )
    except Exception as exc:
        print(f"[警告] xlsx 写出失败：{exc}")

    by_class: Dict[str, int] = {}
    for r in records.values():
        by_class[r["class"]] = by_class.get(r["class"], 0) + 1
    print("分类统计:", json.dumps(by_class, ensure_ascii=False))
    print(f"共 {len(records)} 条 POI")


def main() -> None:
    ap = argparse.ArgumentParser(description="百度 Agent Plan POI 抓取（研究区）")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--checkpoint", default=str(DEFAULT_CHECKPOINT))
    ap.add_argument("--grid-x", type=int, default=6)
    ap.add_argument("--grid-y", type=int, default=5)
    ap.add_argument("--max-calls", type=int, default=980)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--resume", action="store_true")
    args = ap.parse_args()

    token = os.environ.get("BAIDU_MAP_AUTH_TOKEN", "").strip()
    if not token:
        print("错误：需要环境变量 BAIDU_MAP_AUTH_TOKEN", file=sys.stderr)
        sys.exit(2)

    out_dir = Path(args.out_dir)
    client = AgentPlanClient(token, sleep=args.sleep, max_calls=args.max_calls)
    records = crawl(client, out_dir, Path(args.checkpoint), args.grid_x, args.grid_y, args.resume)
    if records:
        write_outputs(records, out_dir)


if __name__ == "__main__":
    main()
