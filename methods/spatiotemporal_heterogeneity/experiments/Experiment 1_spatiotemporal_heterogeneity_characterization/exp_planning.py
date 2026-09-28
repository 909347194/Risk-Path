#!/usr/bin/env python3
"""Exp1 规划层：单次 TD-RiskA*、路径度量、权重敏感性扫描。"""
from __future__ import annotations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from algorithms.a_star.astar_4d import AStar4D


def plan_one(grid, env, planner_cfg, od, t_idx):
    planner = AStar4D(grid, env, planner_cfg)
    return planner.search((od[0], od[1], od[2], t_idx), (od[3], od[4], od[5]))


def path_xy(res):
    """从搜索结果抽取路径 (x, y) 序列（用于叠加到 2D 风险图）。"""
    if res.get("status") != "success":
        return [], []
    xs = [p["coords"][0] for p in res["path"]]
    ys = [p["coords"][1] for p in res["path"]]
    return xs, ys


def path_cells_m(res, grid):
    """路径经过的网格单元 → 物理坐标（米）。"""
    xs, ys = path_xy(res)
    if not xs:
        return np.zeros((0, 2))
    return np.column_stack([np.asarray(xs) * grid.spatial.dx,
                            np.asarray(ys) * grid.spatial.dy])


def mean_deviation_m(cells_a: np.ndarray, cells_b: np.ndarray) -> float:
    """两条路径的平均偏离距离（米）：A 每个点到 B 最近点的距离均值（双向平均）。"""
    if len(cells_a) == 0 or len(cells_b) == 0:
        return float("nan")
    d = np.sqrt(((cells_a[:, None, :] - cells_b[None, :, :]) ** 2).sum(-1))
    return float(d.min(axis=1).mean() + d.min(axis=0).mean()) / 2.0


def run_sensitivity(grid, env, base_cfg, od, hours, w_fatal_values):
    """权重敏感性扫描：w_fatal 变化 → 4 个出发时刻路径长度极差。

    用于回答「路径随出发时刻变化」是不是挑参数挑出来的：沿风险规避程度
    扫描会依次出现三种机制
        (1) 全直飞 regime：所有时刻都走近直线，极差 ≈ 0
        (2) 混合 regime：出发时刻决定是否绕行（极差大）— 路线同伦类切换
        (3) 全绕行 regime：所有时刻都绕开核心，极差又变小
    """
    rows = []
    for wf in w_fatal_values:
        cfg_i = dict(base_cfg)
        cfg_i["w_fatality"] = float(wf)
        cfg_i["w_property"] = float(wf) * 0.4
        cfg_i["w_noise"] = float(wf) * 0.25
        lengths = {}
        for h in hours:
            t_idx = grid.get_time_index(h)
            res = plan_one(grid, env, cfg_i, od, t_idx)
            lengths[h] = (round(float(res["total_distance"]), 1)
                          if res.get("status") == "success" else float("nan"))
        vals = list(lengths.values())
        row = {"w_fatal": wf, "ratio": round(wf / base_cfg["w_distance"], 1)}
        for h in hours:
            row[f"L_{h:02d}h"] = lengths[h]
        row["spread_m"] = round(max(vals) - min(vals), 1)
        row["spread_pct"] = round(100.0 * (max(vals) - min(vals)) / min(vals), 2)
        rows.append(row)
        print(f"    w_fatal={wf:5.1f} ratio={row['ratio']:6.1f} -> "
              f"spread={row['spread_m']:7.1f} m ({row['spread_pct']:5.2f}%)  L={lengths}")
    return rows
