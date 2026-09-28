#!/usr/bin/env python3
"""Exp1 指标层：CSV 序列化、指标/路径差异/异质性统计。"""
from __future__ import annotations

from itertools import combinations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from exp_planning import path_cells_m, mean_deviation_m


def _to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join(str(r.get(c, "")) for c in cols))
    return "\n".join(lines) + "\n"


def write_csv(path, rows: list[dict]) -> None:
    path.write_text(_to_csv(rows), encoding="utf-8")


def metrics_rows(hours, results) -> list[dict]:
    """逐出发时刻的规划指标行。"""
    rows = []
    for h, res in zip(hours, results):
        row = {"departure_hour": h}
        if res.get("status") == "success":
            row.update({
                "status": "success",
                "path_length_m": round(float(res["total_distance"]), 3),
                "survival": round(float(res["final_p_survival"]), 6),
                "cum_fatality": round(float(res["cum_fatality"]), 8),
                "cum_property": round(float(res["cum_property"]), 8),
                "cum_noise": round(float(res["cum_noise"]), 8),
                "cumulative_hazard": round(float(res["cumulative_hazard"]), 6),
                "nodes_explored": int(res["nodes_explored"]),
                "runtime_s": round(float(res["time_cost"]), 3),
            })
        else:
            row.update({"status": "failed", "reason": res.get("reason", "")})
        rows.append(row)
    return rows


def path_difference_rows(hours, results, grid, rows: list[dict]) -> list[dict]:
    """两两路径对比（证明「路径确实随出发时刻改变」）。"""
    diff_rows = []
    cells = {h: path_cells_m(r, grid) for h, r in zip(hours, results)
             if r.get("status") == "success"}
    for h1, h2 in combinations(sorted(cells), 2):
        diff_rows.append({
            "departure_hour_a": h1,
            "departure_hour_b": h2,
            "length_diff_m": round(abs(
                rows[[r["departure_hour"] for r in rows].index(h1)]["path_length_m"]
                - rows[[r["departure_hour"] for r in rows].index(h2)]["path_length_m"]), 3),
            "mean_deviation_m": round(mean_deviation_m(cells[h1], cells[h2]), 3),
        })
    return diff_rows


def heterogeneity_stats(p_crash, z_layer, hours, grid):
    """量化风险场在给定高度层上的空间异质性与时间异质性。"""
    slabs = np.stack([p_crash[:, :, z_layer, grid.get_time_index(h)] for h in hours])
    spatial_cv = [float(s.std() / s.mean()) if s.mean() > 0 else 0.0 for s in slabs]
    # 时间维：逐格点跨出发时刻的变异系数，取中位数（对离群稳健）
    per_cell_cv = slabs.std(axis=0) / np.maximum(slabs.mean(axis=0), 1e-12)
    temporal_cv_median = float(np.median(per_cell_cv))
    # 时间维：逐格点跨出发时刻的相对极差（max-min)/mean 的中位数
    rng = (slabs.max(axis=0) - slabs.min(axis=0)) / np.maximum(slabs.mean(axis=0), 1e-12)
    temporal_range_median = float(np.median(rng))
    return {
        "spatial_cv_per_hour": {h: round(v, 4) for h, v in zip(hours, spatial_cv)},
        "temporal_cv_median": round(temporal_cv_median, 4),
        "temporal_relative_range_median": round(temporal_range_median, 4),
    }


def heterogeneity_rows(het: dict) -> list[dict]:
    het_rows = [{"metric": k, "value": v} for k, v in het.items()]
    het_rows.append({"metric": "spatial_cv_per_hour(detail)", "value": ""})
    for h, v in het["spatial_cv_per_hour"].items():
        het_rows.append({"metric": f"  spatial_cv_{h:02d}h", "value": v})
    return het_rows
