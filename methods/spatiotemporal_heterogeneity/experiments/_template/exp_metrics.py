#!/usr/bin/env python3
"""实验指标层（通用件）：CSV 序列化 + 指标行构造。实验专属统计在本文件追加。"""
from __future__ import annotations

from exp_common import MODULE_ROOT  # noqa: F401


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
    """逐出发时刻的规划指标行（通用字段，按需增删）。"""
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


# TODO: 实验专属的统计/检验（显著性、消融对比、异质性指标……）
