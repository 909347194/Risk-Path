#!/usr/bin/env python3
"""实验规划层（通用件）：单次 TD-RiskA* 与路径度量。实验专属扫描逻辑在本文件追加。"""
from __future__ import annotations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from algorithms.a_star.astar_4d import AStar4D


def plan_one(grid, env, planner_cfg, od, t_idx):
    """单次搜索：od=(x0,y0,z0,x1,y1,z1)，t_idx 为出发时间片。"""
    planner = AStar4D(grid, env, planner_cfg)
    return planner.search((od[0], od[1], od[2], t_idx), (od[3], od[4], od[5]))


def path_xy(res):
    """从搜索结果抽取路径 (x, y) 序列。"""
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
    """两条路径的平均偏离距离（米），双向最近点均值。"""
    if len(cells_a) == 0 or len(cells_b) == 0:
        return float("nan")
    d = np.sqrt(((cells_a[:, None, :] - cells_b[None, :, :]) ** 2).sum(-1))
    return float(d.min(axis=1).mean() + d.min(axis=0).mean()) / 2.0


# TODO: 实验专属的扫描/对照逻辑（参数扫描、消融、多算法对比……）
