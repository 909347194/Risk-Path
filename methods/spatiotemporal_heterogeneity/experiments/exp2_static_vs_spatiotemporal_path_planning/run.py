#!/usr/bin/env python3
"""
Exp 2 — Static Risk vs Spatiotemporal Risk（核心实验）
=====================================================

回答审稿人的第一反应：「为什么不用时间平均的静态风险图？」

三组公平对照（同一 OD、同一 A*、同一权重，仅「风险项的时间口径」不同）：
  M1 distance_only  J = L = Σ d_k                    —— Distance-only A*（基础 baseline）
  M2 static_risk    J = L + λ·C̄(x_k,y_k,z_k)         —— Static Risk A*，C̄ = (1/T)Σ_t C(x,y,z,t)
  M3 spatiotemporal J = L + λ·C(x_k,y_k,z_k,t_k)     —— Spatiotemporal Risk A*（本文方法）

三种方法在 08/12/18/22 四个出发时刻分别规划（共 12 次搜索），
所有路径统一在**真实时空风险场**上后评估（evaluate_path，口径与
astar_4d._expand_node 一致），保证公平比较。

判读原则（重要）：主结果是 R_ST < R_static（安全收益），长度是代价项
（L_ST ≈ L_static 或略长）——「ST 路径更短」不是卖点，不这样解读。

模块结构（与 Exp1 同构）：
  exp_config.py    配置加载（extends 继承）
  exp_data.py      真实数据只读加载 + 降雨情景
  exp_planning.py  M1/M2/M3 规划 + 统一后评估 + 路径差异度量
  exp_metrics.py   Table 1 / 汇总 / 路径差异 / 后悔值
  plot/            fig1 路径决策对比、fig2 六指标柱状、fig3 适应性曲线

运行：python3 run.py
产物：results/fig1_paths.png, fig2_method_bars.png, fig3_adaptation.png,
      table1_main_results.csv, summary.csv, path_difference.csv, regret.csv
"""
from __future__ import annotations

import time as _time

import numpy as np
import yaml

from exp_common import HERE, MODULE_ROOT, RESULT_DIR
from exp_config import load_exp_config
from exp_data import load_experiment_data
from exp_planning import (METHODS, build_static_env, evaluate_path,
                          make_planner_cfg, plan_one, path_cells_m)
from exp_metrics import (table1_rows, summary_rows, path_difference_rows,
                         regret_rows, write_csv, METHOD_LABELS)
from exp_localized_hazard import inject_localized_temporal_hazard, describe
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

    # 1) 网格与数据（与 Exp1 相同的真实数据装载，只读）
    grid = get_macro_grid() if params.get("grid", "macro") == "macro" else get_micro_grid()
    data_type = (cfg.get("data") or {}).get("type", "real")
    pr = load_experiment_data(grid, data_type, params, cfg.get("rain_environment"))

    # 2) 真实时空风险张量 + M2 的时间平均静态场
    out_dir = RESULT_DIR
    out_dir.mkdir(exist_ok=True)
    resolved_path = out_dir / "_resolved_config.yaml"
    resolved_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")

    t0 = _time.time()
    risk = build_risk_tensors(pr, grid,
                              flight_altitude=params.get("flight_altitude", 60.0),
                              config_path=resolved_path)
    print(f"[Risk] tensors built in {_time.time()-t0:.1f}s")

    # 局部时间热点情景（Exp2 专用）：在指定区域/时段注入局部高风险脉冲，
    # 让 ST 在活跃时刻绕开、冷时段走直线，从而产生 ST≠Static 且跨时刻改路证据。
    lh = params.get("localized_hazard")
    if lh and lh.get("enabled"):
        risk = inject_localized_temporal_hazard(risk, grid, lh)
        print(f"[Scenario] {describe(lh)}")

    env_true = EnvTensor(p_crash=risk["p_crash"], fatality=risk["fatality"],
                         property=risk["property"], noise=risk["noise"],
                         obstacle=risk.get("obstacle"), grid=grid)
    env_static = build_static_env(env_true)

    # 3) 三种方法 × 四个出发时刻（同一 OD、同一权重口径）
    od = params["od"]
    hours = params["departure_hours"]
    z_layer = params.get("z_layer", 5)
    cfgs = {m: make_planner_cfg(params, m, grid) for m in METHODS}
    envs = {
        "distance_only": env_true,        # J 不含风险项 → 用哪个场不影响目标，统一用真实场
        "static_risk": env_static,        # 在时间平均场上规划（M2）
        "spatiotemporal": env_true,       # 在真实时空场上规划（M3）
    }

    evaluated: dict = {m: {} for m in METHODS}
    runtime: dict = {m: {} for m in METHODS}
    paths: dict = {h: {} for h in hours}
    cells: dict = {m: {} for m in METHODS}      # 路径物理坐标（路径差异度量用）

    print(f"\n[Planning] OD {od} | {len(hours)} departure times × {len(METHODS)} methods")
    for method in METHODS:
        for h in hours:
            t_idx = grid.get_time_index(h)
            res = plan_one(grid, envs[method], cfgs[method], od, t_idx)
            runtime[method][h] = float(res.get("time_cost", float("nan")))
            ev = evaluate_path(res, env_true, grid, uav_speed=float(params.get("uav_speed", 10.0)))
            evaluated[method][h] = ev
            paths[h][method] = res
            cells[method][h] = path_cells_m(res, grid)
            if ev["status"] == "success":
                print(f"  {METHOD_LABELS[method]:26s} {h:02d}:00  "
                      f"L={ev['distance_m']:8.1f} m  H={ev['cum_hazard']:.4f}  "
                      f"P_surv={ev['survival']:.4f}  t_plan={runtime[method][h]:.1f}s")
            else:
                print(f"  {METHOD_LABELS[method]:26s} {h:02d}:00  FAILED: {ev.get('reason')}")

    # 4) 可视化（fig1 = 论文 Figure 2：same OD + different departure time
    #    + different risk model → different route decisions）
    plot_fig1(grid, risk["p_crash"], paths, hours, z_layer, od, out_dir / "fig1_paths.png")
    rows = table1_rows(evaluated, runtime, hours)
    plot_fig2(rows, hours, out_dir / "fig2_method_bars.png")
    plot_fig3(evaluated, hours, out_dir / "fig3_adaptation.png")

    # 5) 指标导出（Table 1 为主结果表）
    write_csv(out_dir / "table1_main_results.csv", rows)
    summ = summary_rows(rows)
    write_csv(out_dir / "summary.csv", summ)
    diff_rows = path_difference_rows(hours, cells, grid)
    write_csv(out_dir / "path_difference.csv", diff_rows)
    regrets = regret_rows(evaluated, hours)
    write_csv(out_dir / "regret.csv", regrets)
    print(f"\n[Outputs] {out_dir}/fig1_paths.png, fig2_method_bars.png, fig3_adaptation.png")
    print(f"[Metrics] {out_dir}/table1_main_results.csv, summary.csv, "
          "path_difference.csv, regret.csv")

    print("\n[Summary] (mean over departure times, unified true-field evaluation)")
    for r in summ:
        print(f"  {r}")

    # 6) 结论（判读原则见 README §4）：主结果是 R_ST < R_static（安全收益），
    #    长度是代价项（L_ST ≈ L_static 或略长）；「更短」不是卖点。
    st, sta = evaluated.get("spatiotemporal", {}), evaluated.get("static_risk", {})
    lines, wins, dls, n_ok = [], 0, [], 0
    for h in hours:
        e_st, e_sta = st.get(h, {}), sta.get(h, {})
        if e_st.get("status") != "success" or e_sta.get("status") != "success":
            lines.append(f"  {h:02d}:00  (incomplete: ST={e_st.get('status')}, "
                         f"static={e_sta.get('status')})")
            continue
        n_ok += 1
        d_h = e_sta["cum_hazard"] - e_st["cum_hazard"]       # >0 = ST 更安全
        d_l = 100.0 * (e_st["distance_m"] - e_sta["distance_m"]) / e_sta["distance_m"]
        wins += int(d_h > 0)
        dls.append(d_l)
        lines.append(f"  {h:02d}:00  ΔH(static−ST)={d_h:+.4f}  ΔL(ST vs static)={d_l:+.2f}%  "
                     f"P_surv {e_sta['survival']:.4f}→{e_st['survival']:.4f}")
    print("\n[Conclusion] trade-off vs Static-Risk (per departure time):")
    for line in lines:
        print(line)
    if n_ok:
        mean_dl = float(np.mean(dls))
        print(f"  R_ST < R_static at {wins}/{n_ok} departure times; "
              f"mean ΔL(ST vs static) = {mean_dl:+.2f}%")
        if wins == n_ok:
            print("  -> risk-aware trade-off holds: spatiotemporal planning lowers risk "
                  "at comparable length (do NOT read 'shorter' as the win condition).")
        else:
            print("  -> trade-off NOT uniform across departure times; "
                  "inspect per-hour ΔH above before claiming dominance.")

    # 6b) 路径决策证据：D(P_static,P_ST) 与 path-change rate
    st_pair = [r for r in diff_rows
               if r["scope"] == "methods_at_hour"
               and r["method_a"] == METHOD_LABELS["static_risk"]
               and r["method_b"] == METHOD_LABELS["spatiotemporal"]]
    if st_pair:
        devs = [r["mean_deviation_m"] for r in st_pair]
        chgs = [r["path_change_rate"] for r in st_pair]
        print(f"\n[Path decision] D(P_static,P_ST) per hour: "
              f"{ {r['hour_a']: r['mean_deviation_m'] for r in st_pair} }")
        print(f"  path-change rate (static vs ST): "
              f"{ {r['hour_a']: r['path_change_rate'] for r in st_pair} }")
        st_across = [r for r in diff_rows
                     if r["scope"] == "hours_per_method"
                     and r["method_a"] == METHOD_LABELS["static_risk"]]
        stst_across = [r for r in diff_rows
                       if r["scope"] == "hours_per_method"
                       and r["method_a"] == METHOD_LABELS["spatiotemporal"]]
        static_chg = max((r["path_change_rate"] for r in st_across), default=float("nan"))
        st_chg = max((r["path_change_rate"] for r in stst_across), default=float("nan"))
        print(f"  max path-change rate across departure times: "
              f"static={static_chg:.2f} (期望 0：无法适应时间), ST={st_chg:.2f}")
        cell_diag = float(np.hypot(grid.spatial.dx, grid.spatial.dy))
        changed = [c for c in chgs if c >= 0.10]
        if changed:
            verdict = (f"clear route change at {len(changed)}/{len(chgs)} departure times "
                       f"(change-rate ≥ 0.10; cell diagonal {cell_diag:.0f} m)")
        elif max(chgs, default=0.0) > 0:
            verdict = (f"only local within-corridor adjustments (max change-rate "
                       f"{max(chgs):.2f} < 0.10; cell diagonal {cell_diag:.0f} m) — "
                       "routes largely coincide for this OD; heterogeneity is exploited "
                       "via local detours, not corridor switches")
        else:
            verdict = ("paths coincide (change-rate = 0) — heterogeneity did not "
                       "translate into route changes for this OD")
        print(f"  -> same OD + different departure time + different risk model -> " + verdict)


if __name__ == "__main__":
    main()
