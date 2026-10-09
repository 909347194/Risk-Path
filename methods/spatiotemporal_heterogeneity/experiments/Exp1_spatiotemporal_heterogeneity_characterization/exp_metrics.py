#!/usr/bin/env python3
"""Exp1 指标层：CSV 序列化、指标/路径差异/异质性统计。"""
from __future__ import annotations

import csv
import io
from itertools import combinations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from exp_planning import path_cells_m, mean_deviation_m


def _to_csv(rows: list[dict]) -> str:
    """标准 CSV 序列化（csv 模块带引号转义，含逗号的字段不会截断列）。"""
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    for r in rows:
        writer.writerow({c: r.get(c, "") for c in rows[0].keys()})
    return buf.getvalue()


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
    """量化风险场在给定高度层上的空间异质性与时间异质性。

    时间指标给两套口径（修复 M4 所述的命名误读问题）：
      - ``*_all_slices``：全部 nt 个时相（96 × 15 min，与 Figure 5 连续演化口径一致）；
      - ``*_at_departures``：仅本次实验的出发时刻切片（与路径对比口径一致）。
    每套口径都附样本数 ``temporal_n_slices_*``，引用时先看样本数再看数值。
    """
    nt_all = int(p_crash.shape[3])
    slab_all = p_crash[:, :, z_layer, :]                     # (nx, ny, nt_all)
    # 出发时刻切片 (nx, ny, n_departures)
    slabs = np.stack(
        [p_crash[:, :, z_layer, grid.get_time_index(h)] for h in hours], axis=-1)
    spatial_cv = [float(s.std() / s.mean()) if s.mean() > 0 else 0.0
                  for s in np.moveaxis(slabs, -1, 0)]

    def _temporal(arr: np.ndarray) -> tuple[float, float]:
        """逐格点跨时间的 CV / 相对极差，取中位数（对离群稳健）。"""
        mean = np.maximum(arr.mean(axis=-1), 1e-12)
        cv = float(np.median(arr.std(axis=-1) / mean))
        rng = float(np.median((arr.max(axis=-1) - arr.min(axis=-1)) / mean))
        return cv, rng

    cv_all, rng_all = _temporal(slab_all)
    cv_dep, rng_dep = _temporal(slabs)
    return {
        "spatial_cv_per_hour": {h: round(v, 4) for h, v in zip(hours, spatial_cv)},
        "temporal_cv_median_all_slices": round(cv_all, 4),
        "temporal_relative_range_median_all_slices": round(rng_all, 4),
        "temporal_n_slices_all": nt_all,
        "temporal_cv_median_at_departures": round(cv_dep, 4),
        "temporal_relative_range_median_at_departures": round(rng_dep, 4),
        "temporal_n_slices_at_departures": len(hours),
    }


def heterogeneity_rows(het: dict) -> list[dict]:
    het_rows = [{"metric": k, "value": v} for k, v in het.items()]
    het_rows.append({"metric": "spatial_cv_per_hour(detail)", "value": ""})
    for h, v in het["spatial_cv_per_hour"].items():
        het_rows.append({"metric": f"  spatial_cv_{h:02d}h", "value": v})
    return het_rows
