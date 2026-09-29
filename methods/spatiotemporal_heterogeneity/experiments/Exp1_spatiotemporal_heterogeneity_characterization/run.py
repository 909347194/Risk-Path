#!/usr/bin/env python3
"""
Exp 1 — 时空异质性表征 (Spatiotemporal Heterogeneity Characterization)
=========================================================================

目的
----
回答论文证据链的第一个问题：**风险场是否明显随空间和时间同时变化？**

    Cost(x,y,z,t) = P_crash(x,y,z,t) · [fatality + property] + noise

数据源：真实数据（data/02_processed 顶层「已准备好」的数组，**只读加载**），
宏观网格 100×100×12（dx=48.459 m, dy=47.936 m），96 时相 × 15 min。

模块结构
--------
  exp_config.py     配置加载（extends 继承）
  exp_data.py       真实数据只读加载 + 降雨情景
  exp_planning.py   TD-RiskA* 规划、路径度量、权重敏感性
  exp_metrics.py    CSV 指标 / 路径差异 / 异质性统计
  plot/             全部可视化（fig1–fig4）

运行：python3 run.py
产物：results/fig1–fig4*.png, metrics.csv, heterogeneity.csv,
      path_difference.csv, sensitivity.csv
"""
from __future__ import annotations

import sys
import time as _time

import numpy as np
import yaml

from exp_common import HERE, MODULE_ROOT, RESULT_DIR
from exp_config import load_exp_config
from exp_data import load_experiment_data
from exp_planning import plan_one, run_sensitivity
from exp_metrics import (metrics_rows, path_difference_rows,
                         heterogeneity_stats, heterogeneity_rows, write_csv)
from plot import plot_fig1, plot_fig2, plot_fig3, plot_fig4

from tensor_engine.grid_system import get_macro_grid, get_micro_grid
from tensor_engine.risk_tensor_assembler import build_risk_tensors
from tensor_engine.wind_environment import get_wind_environment, _compute_svf
from algorithms.env_tensor import EnvTensor


def _req(params: dict, key: str) -> float:
    """权重必须来自 config.yaml 显式给定；缺键报错，禁止静默落到默认 regime。"""
    if key not in params:
        raise KeyError(f"config.yaml params.{key} 缺失——权重类参数必须显式给定，"
                       "默认值会静默改变 w_risk/w_ops regime，实验不可比")
    return float(params[key])


def main() -> None:
    cfg = load_exp_config(HERE / "config.yaml")
    exp = cfg.get("experiment", {})
    params = cfg.get("params", {})
    print("=" * 72)
    print(f"exp 1: {exp.get('name')} — {exp.get('description')}")
    print("=" * 72)

    # 1) 网格：真实数据 → 宏观网格（精确分辨率 48.459 × 47.936 m）
    grid = get_macro_grid() if params.get("grid", "macro") == "macro" else get_micro_grid()
    print("\n[Grid]")
    print(grid.summary())

    # 2) 数据：真实数据只读加载（synthetic 才走 DataPipeline）
    data_type = (cfg.get("data") or {}).get("type", "real")
    t0 = _time.time()
    pr = load_experiment_data(grid, data_type, params, cfg.get("rain_environment"))
    print(f"[Data] done in {_time.time()-t0:.1f}s; "
          f"rain enabled={bool((params.get('rain') or {}).get('enabled', cfg.get('rain_environment', {}).get('enabled', True)))}")

    # 3) 组装四维风险张量（情景化风场，继承 common.yaml wind_environment）
    #    把「实验配置 + 公共配置」合并后落盘，保证 build_risk_tensors 拿到完整参数。
    resolved = load_exp_config(HERE / "config.yaml")
    out_dir = RESULT_DIR
    out_dir.mkdir(exist_ok=True)
    resolved_path = out_dir / "_resolved_config.yaml"
    resolved_path.write_text(yaml.safe_dump(resolved, allow_unicode=True), encoding="utf-8")

    t1 = _time.time()
    risk = build_risk_tensors(
        pr, grid,
        flight_altitude=params.get("flight_altitude", 60.0),
        config_path=resolved_path,
    )
    print(f"\n[Risk] tensors built in {_time.time()-t1:.1f}s")
    pc = risk["p_crash"]
    print(f"  p_crash range=[{pc.min():.3e}, {pc.max():.3e}]")

    # 4) 风场张量（Figure 2 驱动因子可视化）
    wind_env = get_wind_environment(resolved.get("wind_environment"),
                                    scenario_name=params.get("wind_scenario"))
    wind_4d = wind_env.build_wind_tensor(
        grid=grid, building_heights=pr.building_heights,
        svf=_compute_svf(pr.building_heights),
    )

    # 5) 路径规划：同一 OD、多个出发时刻（默认高度自由；可选 60 m 定高锁）
    od = params["od"]
    hours = params["departure_hours"]
    z_layer = params.get("z_layer", 5)
    alt = (z_layer + 1.0) * grid.spatial.dz          # 层中心物理高度

    planner_cfg = {
        "uav_speed": float(params.get("uav_speed", 10.0)),
        "w_distance": _req(params, "w_ops"),
        "w_fatality": _req(params, "w_fatal"),
        "w_property": _req(params, "w_prop"),
        "w_noise": _req(params, "w_noise"),
        "survival_threshold": float(params.get("survival_threshold", 0.0)),
        "max_labels_per_cell": 8,
    }
    if params.get("cruise_altitude_lock", True):
        # 只允许层中心落在 [alt - 0.5·dz, alt + 0.5·dz) 的层 → 锁定 60 m 巡航层
        planner_cfg["min_altitude"] = alt - 0.5 * grid.spatial.dz
        planner_cfg["max_altitude"] = alt + 0.5 * grid.spatial.dz

    env = EnvTensor(
        p_crash=risk["p_crash"], fatality=risk["fatality"],
        property=risk["property"], noise=risk["noise"], grid=grid,
    )

    results = []
    lock_on = bool(params.get("cruise_altitude_lock", False))
    alt_txt = (f"cruise alt {alt:.0f} m (locked)" if lock_on
               else f"altitude unlocked ({grid.spatial.nz} layers, endpoints z={alt:.0f} m)")
    print(f"\n[Planning] OD {od} | {len(hours)} departure times | {alt_txt} | "
          f"w_risk/w_ops={planner_cfg['w_fatality']/planner_cfg['w_distance']:.0f}")
    for h in hours:
        t_idx = grid.get_time_index(h)
        res = plan_one(grid, env, planner_cfg, od, t_idx)
        results.append(res)
        if res.get("status") == "success":
            print(f"  {h:02d}:00  L={res['total_distance']:8.1f} m  "
                  f"P_surv={res['final_p_survival']:.4f}  "
                  f"nodes={res['nodes_explored']:>7}  t={res['time_cost']:.1f}s")
        else:
            print(f"  {h:02d}:00  FAILED: {res.get('reason')}")

    # 6) 可视化（全部由 plot/ 负责）
    plot_fig1(grid, risk["p_crash"], results, hours, z_layer, od, out_dir / "fig1_risk_field.png")
    plot_fig2(grid, wind_4d, pr.rho_population, hours, z_layer, out_dir / "fig2_drivers.png")
    plot_fig3(grid, results, hours, pr.building_heights, od, out_dir / "fig3_path_comparison.png")
    print(f"\n[Figures] {out_dir}/fig1_risk_field.png, fig2_drivers.png, fig3_path_comparison.png")

    # 7) 指标导出
    rows = metrics_rows(hours, results)
    write_csv(out_dir / "metrics.csv", rows)

    # 8) 路径差异量化（两两对比，量化「路径随出发时刻变化」的强弱）
    diff_rows = path_difference_rows(hours, results, grid, rows)
    if diff_rows:
        write_csv(out_dir / "path_difference.csv", diff_rows)

    # 9) 异质性统计
    het = heterogeneity_stats(risk["p_crash"], z_layer, hours, grid)
    write_csv(out_dir / "heterogeneity.csv", heterogeneity_rows(het))

    print(f"[Metrics] {out_dir}/metrics.csv, path_difference.csv, heterogeneity.csv")
    print("\n[Heterogeneity]")
    print(f"  spatial CV of P_crash per hour: {het['spatial_cv_per_hour']}")
    print(f"  temporal CV (median over cells): {het['temporal_cv_median']}")
    print(f"  temporal relative range (median): {het['temporal_relative_range_median']}")

    # 9b) 权重敏感性扫描（检验「路径随时刻变化」对权重选择的稳健性）
    sens = (params.get("sensitivity") or {})
    if sens.get("enabled", False):
        wf_list = sens.get("w_fatal_values") or [params.get("w_fatal", 30.0)]
        print(f"\n[Sensitivity] sweeping w_fatal {wf_list}")
        sens_rows = run_sensitivity(grid, env, planner_cfg, od, hours, wf_list)
        write_csv(out_dir / "sensitivity.csv", sens_rows)
        plot_fig4(sens_rows, hours, out_dir / "fig4_weight_sensitivity.png")
        print(f"[Sensitivity] {out_dir}/sensitivity.csv, fig4_weight_sensitivity.png")

    # 10) 结论
    lengths = [r["path_length_m"] for r in rows if r.get("status") == "success"]
    if len(lengths) > 1:
        spread = max(lengths) - min(lengths)
        max_dev = max((d["mean_deviation_m"] for d in diff_rows), default=0.0)
        print(f"\n[Conclusion] path length spread = {spread:.1f} m "
              f"({100*spread/min(lengths):.1f}% relative); "
              f"max mean deviation between paths = {max_dev:.1f} m -> "
              + ("paths DIFFER by departure time (spatiotemporal heterogeneity matters)."
                 if spread > 1.0 else "paths nearly identical (weak response)."))


if __name__ == "__main__":
    main()
