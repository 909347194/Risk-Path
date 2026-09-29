#!/usr/bin/env python3
"""Exp2 指标层：三方法 × 四时刻的对比表、汇总表、后悔值表。"""
from __future__ import annotations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

METHODS = ("distance_only", "static_risk", "spatiotemporal")
METHOD_LABELS = {
    "distance_only": "Distance-only A*",
    "static_risk": "Static-Risk A*",
    "spatiotemporal": "Spatiotemporal A* (ours)",
}


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


def comparison_rows(evaluated: dict, runtime: dict) -> list[dict]:
    """evaluated[method][hour] = evaluate_path(...) 结果；runtime[method][hour] = 规划耗时。"""
    rows = []
    for method in METHODS:
        for h, ev in evaluated.get(method, {}).items():
            row = {"method": method, "departure_hour": h, "status": ev.get("status")}
            if ev.get("status") == "success":
                row.update({
                    "distance_m": ev["distance_m"],
                    "travel_time_s": ev["travel_time_s"],
                    "risk_cum_hazard": ev["cum_hazard"],
                    "survival": ev["survival"],
                    "cum_fatality": ev["cum_fatality"],
                    "cum_property": ev["cum_property"],
                    "cum_noise": ev["cum_noise"],
                    "planning_runtime_s": round(float(runtime.get(method, {}).get(h, float("nan"))), 3),
                })
            else:
                row.update({"reason": ev.get("reason", "")})
            rows.append(row)
    return rows


def summary_rows(rows: list[dict]) -> list[dict]:
    """每方法跨时刻均值（论文汇总表）。"""
    out = []
    for method in METHODS:
        sub = [r for r in rows if r["method"] == method and r.get("status") == "success"]
        if not sub:
            out.append({"method": METHOD_LABELS[method], "n_success": 0})
            continue
        out.append({
            "method": METHOD_LABELS[method],
            "n_success": len(sub),
            "distance_m_mean": round(float(np.mean([r["distance_m"] for r in sub])), 1),
            "risk_cum_hazard_mean": round(float(np.mean([r["risk_cum_hazard"] for r in sub])), 4),
            "survival_mean": round(float(np.mean([r["survival"] for r in sub])), 4),
            "travel_time_s_mean": round(float(np.mean([r["travel_time_s"] for r in sub])), 1),
            "planning_runtime_s_mean": round(float(np.mean([r["planning_runtime_s"] for r in sub])), 2),
        })
    return out


def regret_rows(evaluated: dict) -> list[dict]:
    """逐时刻「安全后悔值」：相对时空感知方法的存活率差距（越大说明静态/距离越危险）。"""
    rows = []
    base = evaluated.get("spatiotemporal", {})
    for h, ev_base in base.items():
        if ev_base.get("status") != "success":
            continue
        for method in ("distance_only", "static_risk"):
            ev = evaluated.get(method, {}).get(h)
            if not ev or ev.get("status") != "success":
                continue
            rows.append({
                "departure_hour": h,
                "method": method,
                "survival_gap": round(ev_base["survival"] - ev["survival"], 6),
                "hazard_excess": round(ev["cum_hazard"] - ev_base["cum_hazard"], 6),
            })
    return rows
