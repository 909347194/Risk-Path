#!/usr/bin/env python3
"""Exp2 指标层：Table 1 主结果表、汇总表、路径差异表、安全后悔值表。

对应论文输出：
  table1_main_results.csv → Table 1（Time | Method | Length | Fatal | Property |
                            Noise | Survival | Runtime，主结果表）
  summary.csv             → 跨出发时刻均值（含相对 Static-Risk 的风险/长度对比）
  path_difference.csv     → D(P_static,P_ST) 与 path-change rate
                           （风险模型/出发时刻是否真的改变了路径决策）
  regret.csv              → 逐时刻安全后悔值（相对时空感知方法）
"""
from __future__ import annotations

import csv
import io
from itertools import combinations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from exp_planning import mean_deviation_m, path_change_rate

METHODS = ("distance_only", "static_risk", "spatiotemporal")
METHOD_LABELS = {
    "distance_only": "Distance-only A*",
    "static_risk": "Static-Risk A*",
    "spatiotemporal": "Spatiotemporal A* (ours)",
}


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


def table1_rows(evaluated: dict, runtime: dict, hours: list) -> list[dict]:
    """Table 1 主结果：departure_hour × method。

    前 8 列即论文 Table 1 口径（Time | Method | Length | Fatal risk | Property |
    Noise | Survival | Runtime）；hazard_H / travel_time_s / status / reason 为
    附加诊断列（结论判定用 H，失败行需要 reason）。
    """
    rows = []
    for h in hours:
        for method in METHODS:
            ev = evaluated.get(method, {}).get(h, {})
            row = {"departure_hour": h, "method": METHOD_LABELS[method]}
            if ev.get("status") == "success":
                row.update({
                    "length_m": ev["distance_m"],
                    "fatal_risk": ev["cum_fatality"],
                    "property_risk": ev["cum_property"],
                    "noise_risk": ev["cum_noise"],
                    "survival": ev["survival"],
                    "runtime_s": round(float(runtime.get(method, {}).get(h, float("nan"))), 3),
                    "hazard_H": ev["cum_hazard"],
                    "travel_time_s": ev["travel_time_s"],
                    "status": "success",
                    "reason": "",
                })
            else:
                row.update({
                    "length_m": "", "fatal_risk": "", "property_risk": "", "noise_risk": "",
                    "survival": "", "runtime_s": round(float(runtime.get(method, {}).get(h, float("nan"))), 3),
                    "hazard_H": "", "travel_time_s": "",
                    "status": "failed", "reason": ev.get("reason", ""),
                })
            rows.append(row)
    return rows


def summary_rows(rows: list[dict]) -> list[dict]:
    """每方法跨出发时刻均值 + 相对 Static-Risk 的对比列。

    hazard_vs_static_pct：H_static − H_method（>0 = 比静态更安全，% of H_static）；
    length_vs_static_pct：L_method − L_static（>0 = 比静态更长，代价项）。
    判读原则：主看风险下降（前者 > 0），长度是代价（见 README §4）。
    """
    def _mean(vals):
        return round(float(np.mean(vals)), 4) if vals else ""

    ok = {m: [r for r in rows
              if r["method"] == METHOD_LABELS[m] and r.get("status") == "success"]
          for m in METHODS}
    h_static = _mean([r["hazard_H"] for r in ok["static_risk"]])
    l_static = _mean([r["length_m"] for r in ok["static_risk"]])

    out = []
    for m in METHODS:
        sub = ok[m]
        if not sub:
            out.append({"method": METHOD_LABELS[m], "n_success": 0})
            continue
        h_m = _mean([r["hazard_H"] for r in sub])
        l_m = _mean([r["length_m"] for r in sub])
        row = {
            "method": METHOD_LABELS[m],
            "n_success": len(sub),
            "length_m_mean": _mean([r["length_m"] for r in sub]),
            "fatal_risk_mean": _mean([r["fatal_risk"] for r in sub]),
            "property_risk_mean": _mean([r["property_risk"] for r in sub]),
            "noise_risk_mean": _mean([r["noise_risk"] for r in sub]),
            "survival_mean": _mean([r["survival"] for r in sub]),
            "runtime_s_mean": _mean([r["runtime_s"] for r in sub]),
            "hazard_H_mean": h_m,
        }
        if h_static != "" and l_static not in ("", 0):
            row["hazard_vs_static_pct"] = round(100.0 * (h_static - h_m) / h_static, 2)
            row["length_vs_static_pct"] = round(100.0 * (l_m - l_static) / l_static, 2)
        else:
            row["hazard_vs_static_pct"] = ""
            row["length_vs_static_pct"] = ""
        out.append(row)
    return out


def path_difference_rows(hours: list, cells: dict, grid) -> list[dict]:
    """路径差异表（回答「风险模型/出发时刻是否真的改变了路径决策」）。

    两类行（scope 列区分）：
      - methods_at_hour：同一出发时刻、方法两两对比（核心：D(P_static,P_ST)）；
      - hours_per_method：同一方法、不同出发时刻对比（决策是否随时刻改变；
        Static 的路径不依赖出发时刻，理论上 change-rate ≡ 0）。
    path_change_rate：到对方路径最近点 > 1 格对角线的采样点占比（双向平均）。
    """
    cell_diag = float(np.hypot(grid.spatial.dx, grid.spatial.dy))
    rows = []

    def _pair_row(scope, m1, m2, h1, h2):
        a = cells.get(m1, {}).get(h1)
        b = cells.get(m2, {}).get(h2)
        if a is None or b is None or len(a) == 0 or len(b) == 0:
            return
        rows.append({
            "scope": scope,
            "method_a": METHOD_LABELS[m1],
            "method_b": METHOD_LABELS[m2],
            "hour_a": h1,
            "hour_b": h2,
            "mean_deviation_m": round(mean_deviation_m(a, b), 3),
            "path_change_rate": round(path_change_rate(a, b, cell_diag), 4),
        })

    for h in hours:
        for m1, m2 in combinations(METHODS, 2):
            _pair_row("methods_at_hour", m1, m2, h, h)
    for m in METHODS:
        for h1, h2 in combinations(sorted(hours), 2):
            _pair_row("hours_per_method", m, m, h1, h2)
    return rows


def regret_rows(evaluated: dict, hours: list) -> list[dict]:
    """逐时刻「安全后悔值」：相对时空感知方法的存活率差距/风险超额
    （越大说明 static/distance 在该时刻越危险，即静态图付出的安全代价）。"""
    rows = []
    base = evaluated.get("spatiotemporal", {})
    for h in hours:
        ev_base = base.get(h, {})
        if ev_base.get("status") != "success":
            continue
        for method in ("distance_only", "static_risk"):
            ev = evaluated.get(method, {}).get(h, {})
            if ev.get("status") != "success":
                continue
            rows.append({
                "departure_hour": h,
                "method": METHOD_LABELS[method],
                "survival_gap": round(ev_base["survival"] - ev["survival"], 6),
                "hazard_excess": round(ev["cum_hazard"] - ev_base["cum_hazard"], 6),
            })
    return rows
