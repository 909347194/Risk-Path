#!/usr/bin/env python3
"""
Travel 出行数据 -> 项目网格矩阵（研究区）。

输入：data/01_raw/travel/gz_user_counts_risk_analysis_20201022_{0..9}.csv
     （11m 手机信令网格，字段 grid_id,mode,user_counts,lat_*,lon_*,clat,clon；
       _all.csv 无坐标列，故用 0..9 分时段文件）

输出（data/02_processed/）：
  - travel_user_counts.npz : 每模式 (100,100,10) 计数（时段维度 t=0..9）+ total
  - base_vehicle_2d.npy    : (100,100) pt_drive 全时段合计（车辆密度底图 ρ_veh 输入/校验）
  - travel_clip_stats.json : 研究区裁剪统计（覆盖网格、模式占比）

网格约定与 poi_parser/landuse 一致：ix = int((x-minx)/(maxx-minx)*NX)（经度->x）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # Risk-Path/
sys.path.insert(0, str(Path(__file__).resolve().parent))
from grid_constants import BBOX, NX, NY  # noqa: E402

MODULE_ROOT = PROJECT_ROOT / "methods" / "spatiotemporal_heterogeneity"
TRAVEL_DIR = MODULE_ROOT / "data" / "01_raw" / "travel"
OUT_DIR = MODULE_ROOT / "data" / "02_processed"
NT = 10
MODES = ["pt_drive", "bike", "walking", "subway"]


def main() -> None:
    minx, miny, maxx, maxy = BBOX
    counts = {m: np.zeros((NX, NY, NT), dtype=np.float32) for m in MODES}
    stats = {"slices": {}, "modes_in_data": set()}

    for t in range(NT):
        path = TRAVEL_DIR / f"gz_user_counts_risk_analysis_20201022_{t}.csv"
        if not path.exists():
            print(f"[跳过] {path.name} 不存在")
            continue
        n_rows = n_clip = 0
        with open(path, encoding="utf-8") as f:
            header = f.readline().strip().split(",")
            idx = {name: header.index(name) for name in header if name}
            for line in f:
                parts = line.rstrip("\n").split(",")
                if len(parts) < len(header):
                    continue
                n_rows += 1
                clat = float(parts[idx["clat"]])
                clon = float(parts[idx["clon"]])
                if not (minx <= clon <= maxx and miny <= clat <= maxy):
                    continue
                n_clip += 1
                mode = parts[idx["mode"]]
                stats["modes_in_data"].add(mode)
                if mode not in counts:
                    continue
                uc = float(parts[idx["user_counts"]])
                ix = min(NX - 1, int((clon - minx) / (maxx - minx) * NX))
                iy = min(NY - 1, int((clat - miny) / (maxy - miny) * NY))
                counts[mode][ix, iy, t] += uc
        stats["slices"][t] = {"rows": n_rows, "in_bbox": n_clip}
        print(f"[时段 {t}] 总行 {n_rows}，研究区内 {n_clip}")

    stats["modes_in_data"] = sorted(stats["modes_in_data"])
    total = sum(counts.values())
    npz = {m: counts[m] for m in MODES}
    npz["total"] = total
    npz["modes"] = np.asarray(MODES)
    npz["time_slices"] = np.arange(NT)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT_DIR / "travel_user_counts.npz", **npz)

    base_vehicle = counts["pt_drive"].sum(axis=2)
    np.save(OUT_DIR / "base_vehicle_2d.npy", base_vehicle)

    # 研究区统计
    per_mode = {m: float(counts[m].sum()) for m in MODES}
    tot = sum(per_mode.values()) or 1.0
    stats["study_area"] = {
        "per_mode_counts": per_mode,
        "mode_share": {m: round(v / tot, 4) for m, v in per_mode.items()},
        "active_cells_total": int((total.sum(axis=2) > 0).sum()),
        "active_cells_pt_drive": int((base_vehicle > 0).sum()),
    }
    (OUT_DIR / "travel_clip_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("模式占比:", stats["study_area"]["mode_share"])
    print("活跃格数(全部/pt_drive):",
          stats["study_area"]["active_cells_total"], "/",
          stats["study_area"]["active_cells_pt_drive"])
    print("已保存:", OUT_DIR / "travel_user_counts.npz", "+ base_vehicle_2d.npy")


if __name__ == "__main__":
    main()
