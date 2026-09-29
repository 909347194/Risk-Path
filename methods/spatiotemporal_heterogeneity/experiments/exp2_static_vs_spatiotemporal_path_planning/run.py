#!/usr/bin/env python3
"""
Exp 2 — Static Risk vs Spatiotemporal Risk（核心实验）
=====================================================

回答审稿人的第一反应：「为什么不用时间平均的静态风险图？」

三种方法（同一 OD、同一权重口径，仅风险项的时间口径不同）：
  1) distance_only   J = Σ w_d·(d/d_max)                          —— 只看距离
  2) static_risk     J = Σ 风险项(C̄) + w_d·(d/d_max)              —— C̄ = 时间平均风险
  3) spatiotemporal  J = Σ 风险项(C(x_k,y_k,z_k,t_k)) + w_d·(d/d_max) —— 本文方法

三种方法在 08/12/18/22 四个出发时刻分别规划（共 12 次搜索），
所有路径统一在**真实时空风险场**上后评估（evaluate_path，口径与
astar_4d._expand_node 一致），保证公平比较。

模块结构（与 Exp1 同构）：
  exp_config.py   配置加载（extends 继承）
  exp_data.py     真实数据只读加载 + 降雨情景
  exp_planning.py 三方法规划 + 统一后评估
  exp_metrics.py  对比表 / 汇总表 / 后悔值表
  plot/           fig1 路径对比、fig2 指标柱状、fig3 适应性曲线

运行：python3 run.py
产物：results/fig1–fig3*.png, comparison.csv, summary.csv, regret.csv
"""
from __future__ import annotations

import time as _time

import numpy as np
import yaml

from exp_common import HERE, MODULE_ROOT, RESULT_DIR
from exp_config import load_exp_config
from exp_data import load_experiment_data
from exp_planning import (METHODS, build_static_env, evaluate_path,
                          make_planner_cfg, plan_one)
from exp_metrics import (comparison_rows, summary_rows, regret_rows,
                         write_csv, METHOD_LABELS)
from plot import plot_fig1, plot_fig2, plot_fig3

from tensor_engine.grid_system import get_macro_grid, get_micro_grid
from tensor_engine.risk_tensor_assembler import build_risk_tensors
from algorithms.env_tensor import EnvTensor


def main() -> None:
    cfg = load_exp_config(HERE / "config.yaml")
    exp = cfg.get("experiment", {})
    params = cfg.get("params", {})
    print("=" * 72)
    print(f"Exp 2: {exp.get('name')} — {exp.get('description')}")
    print("=" * 72)

    # 1) 网格与数据（与 Exp1 相同的真实数据装载）
    grid = get_macro_grid() if params.get("grid", "macro") == "macro" else get_micro_grid()
    data_type = (cfg.get("data") or {}).get("type", "real")
    pr = load_experiment_data(grid, data_type, params, cfg.get("rain_environment"))

    # 2) 真实时空风险张量
    out_dir = RESULT_DIR
    out_dir.mkdir(exist_ok=True)
    resolved_path = out_dir / "_resolved_config.yaml"
    resolved_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")

    t0 = _time.time()
    risk = build_risk_tensors(pr, grid,
                              flight_altitude=params.get("flight_altitude", 60.0),
                              config_path=resolved_path)
    print(f"[Risk] tensors built in {_time.time()-t0:.1f}s")
    env_true = EnvTensor(p_crash=risk["p_crash"], fatality=risk["fatality"],
                         property=risk["property"], noise=risk["noise"], grid=grid)
    env_static = build_static_env(env_true)

    # 3) 三种方法 × 四个出发时刻
    od = params["od"]
    hours = params["departure_hours"]
    z_layer = params.get("z_layer", 5)
    cfgs = {m: make_planner_cfg(params, m, grid) for m in METHODS}
    envs = {
        "distance_only": env_true,        # 目标不含风险 → 用哪个场无所谓，统一用真实场
        "static_risk": env_static,        # 在时间平均场上规划
        "spatiotemporal": env_true,       # 在真实时空场上规划
    }

    evaluated: dict = {m: {} for m in METHODS}
    runtime: dict = {m: {} for m in METHODS}
    paths: dict = {h: {} for h in hours}

    print(f"\n[Planning] OD {od} | {len(hours)} departure times × {len(METHODS)} methods")
    for method in METHODS:
        for h in hours:
            t_idx = grid.get_time_index(h)
            res = plan_one(grid, envs[method], cfgs[method], od, t_idx)
            runtime[method][h] = float(res.get("time_cost", float("nan")))
            ev = evaluate_path(res, env_true, grid, uav_speed=float(params.get("uav_speed", 10.0)))
            evaluated[method][h] = ev
            paths[h][method] = res
            if ev["status"] == "success":
                print(f"  {METHOD_LABELS[method]:26s} {h:02d}:00  "
                      f"L={ev['distance_m']:8.1f} m  H={ev['cum_hazard']:.4f}  "
                      f"P_surv={ev['survival']:.4f}  t_plan={runtime[method][h]:.1f}s")
            else:
                print(f"  {METHOD_LABELS[method]:26s} {h:02d}:00  FAILED: {ev.get('reason')}")

    # 4) 可视化
    plot_fig1(grid, risk["p_crash"], paths, hours, z_layer, od, out_dir / "fig1_paths.png")
    rows = comparison_rows(evaluated, runtime)
    plot_fig2(rows, hours, out_dir / "fig2_method_bars.png")
    plot_fig3(evaluated, hours, out_dir / "fig3_adaptation.png")

    # 5) 指标导出
    write_csv(out_dir / "comparison.csv", rows)
    summ = summary_rows(rows)
    write_csv(out_dir / "summary.csv", summ)
    regrets = regret_rows(evaluated)
    write_csv(out_dir / "regret.csv", regrets)
    print(f"\n[Outputs] {out_dir}/fig1_paths.png, fig2_method_bars.png, fig3_adaptation.png")
    print(f"[Metrics] {out_dir}/comparison.csv, summary.csv, regret.csv")

    # 6) 结论
    print("\n[Summary] (mean over departure times, true-field evaluation)")
    for r in summ:
        print(f"  {r}")

    if regrets:
        worst = max(regrets, key=lambda r: r["survival_gap"])
        print(f"\n[Conclusion] worst safety regret: {worst['method']} @ {worst['departure_hour']:02d}:00 "
              f"— survival gap = {worst['survival_gap']:.4f}, hazard excess = {worst['hazard_excess']:.4f} "
              "vs spatiotemporal planning.")


if __name__ == "__main__":
    main()
