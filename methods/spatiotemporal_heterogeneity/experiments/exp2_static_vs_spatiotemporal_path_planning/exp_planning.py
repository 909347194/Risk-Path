#!/usr/bin/env python3
"""Exp2 规划层：三种规划目标 + 统一后评估。

三种方法（同一 A*、同一权重，仅「风险项的时间口径」不同）：
  distance_only   J = Σ w_d·(d/d_max)                       （风险权重全 0）
  static_risk     J = Σ 风险项(C̄) + w_d·(d/d_max)           （C̄ = 时间平均）
  spatiotemporal  J = Σ 风险项(C(x_k,y_k,z_k,t_k)) + w_d·(d/d_max)

统一后评估 evaluate_path()：无论用什么目标规划，路径都放回
**真实时空风险场**上按 astar_4d._expand_node 的同一口径重算
（H 累加、存活率、后果项），保证三方法可公平比较。
"""
from __future__ import annotations

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401

from algorithms.a_star.astar_4d import AStar4D
from algorithms.env_tensor import EnvTensor

METHODS = ("distance_only", "static_risk", "spatiotemporal")


def build_static_env(env_true: EnvTensor) -> EnvTensor:
    """时间平均静态风险场：每个分量沿 t 求均值后复制到全部时相。"""

    def avg4d(a: np.ndarray) -> np.ndarray:
        m = a.mean(axis=3, keepdims=True)
        return np.repeat(m, a.shape[3], axis=3)

    return EnvTensor(
        p_crash=avg4d(env_true.p_crash),
        fatality=avg4d(env_true.fatality),
        property=avg4d(env_true.property),
        noise=avg4d(env_true.noise),
        # 建筑是静态的：静态场沿用同一套硬约束，否则对比不公平
        obstacle=env_true.obstacle,
    )


def make_planner_cfg(params: dict, method: str, grid) -> dict:
    """构造三种方法的 planner 配置（目标不同，其余完全一致）。"""
    cfg = {
        "uav_speed": float(params.get("uav_speed", 10.0)),
        "survival_threshold": float(params.get("survival_threshold", 0.0)),
        "max_labels_per_cell": 8,
        "max_iterations": int(params.get("max_iterations", 2_000_000)),
    }
    if method == "distance_only":
        cfg.update({"w_distance": 1.0, "w_fatality": 0.0, "w_property": 0.0, "w_noise": 0.0})
    else:
        cfg.update({
            "w_distance": float(params["w_ops"]),
            "w_fatality": float(params["w_fatal"]),
            "w_property": float(params["w_prop"]),
            "w_noise": float(params["w_noise"]),
        })
    if params.get("cruise_altitude_lock", True):
        z_layer = params.get("z_layer", 5)
        alt = (z_layer + 1.0) * grid.spatial.dz
        cfg["min_altitude"] = alt - 0.5 * grid.spatial.dz
        cfg["max_altitude"] = alt + 0.5 * grid.spatial.dz
    return cfg


def plan_one(grid, env: EnvTensor, cfg: dict, od, t_idx: int) -> dict:
    planner = AStar4D(grid, env, cfg)
    return planner.search((od[0], od[1], od[2], t_idx), (od[3], od[4], od[5]))


def evaluate_path(res: dict, env_true: EnvTensor, grid, uav_speed: float = 10.0) -> dict:
    """把规划出的路径放回真实时空风险场重算全部指标（统一后评估）。

    口径与 astar_4d._expand_node 完全一致：
      每步 dt = dist/uav_speed；进入格 (x2,y2,z2) 的 t2 时刻取 risk_at；
      h_step = -ln(1-p_crash)；H 累加；P_surv = exp(-H)；
      δC_f = P_prior·p_crash·fatality；δC_p 同；δC_n = P_prior·noise·dt。
    """
    if res.get("status") != "success":
        return {"status": res.get("status", "failed"), "reason": res.get("reason", "")}

    nodes = res["path"]
    H, P, cf, cp, cn, dist_total, t_total = 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0
    for a, b in zip(nodes[:-1], nodes[1:]):
        (x1, y1, z1, _), (x2, y2, z2, t2) = a["coords"], b["coords"]
        dist = float(np.sqrt(((x2 - x1) * grid.spatial.dx) ** 2
                             + ((y2 - y1) * grid.spatial.dy) ** 2
                             + ((z2 - z1) * grid.spatial.dz) ** 2))
        dt = dist / uav_speed
        r = env_true.risk_at(x2, y2, z2, t2)
        p = float(np.clip(r["p_crash"], 0.0, 1.0))
        h = -np.log(1.0 - p) if p < 1.0 else np.inf
        cf += P * p * float(r["fatality"])
        cp += P * p * float(r["property"])
        cn += P * float(r["noise"]) * dt
        H += h
        P = float(np.exp(-H))
        dist_total += dist
        t_total += dt

    return {
        "status": "success",
        "distance_m": round(dist_total, 3),
        "travel_time_s": round(t_total, 2),
        "cum_hazard": round(H, 6),
        "survival": round(P, 6),
        "cum_fatality": round(cf, 8),
        "cum_property": round(cp, 8),
        "cum_noise": round(cn, 8),
    }


def path_xy(res: dict):
    if res.get("status") != "success":
        return [], []
    xs = [p["coords"][0] for p in res["path"]]
    ys = [p["coords"][1] for p in res["path"]]
    return xs, ys
