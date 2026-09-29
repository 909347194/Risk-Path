#!/usr/bin/env python3
"""
实验入口模板 — 复制 _template/ 后按需改写。

模块结构（职责分离，勿把逻辑堆回本文件）：
  exp_common.py     路径引导（HERE / MODULE_ROOT / RESULT_DIR）
  exp_config.py     配置加载（extends 继承公共配置）
  exp_data.py       数据装配（真实数据只读加载 / 合成管线）
  exp_planning.py   规划与路径度量
  exp_metrics.py    CSV 指标导出
  plot/             全部可视化（每图一个模块，plot/__init__ 导出）

要点：
1. 配置就在本目录 config.yaml，支持 extends 继承 configs/common.yaml
2. 真实数据用 load_prepared_real_data() 只读加载，不要 run_all()（会覆盖数据）
3. 产物写 result/；可视化一律放 plot/，run.py 只做编排

运行：python3 run.py
"""
from __future__ import annotations

import time as _time

from exp_common import HERE, RESULT_DIR
from exp_config import load_exp_config
from exp_data import load_experiment_data
from exp_planning import plan_one
from exp_metrics import metrics_rows, write_csv
from plot import plot_fig1

from tensor_engine.grid_system import get_macro_grid, get_micro_grid
from tensor_engine.risk_tensor_assembler import build_risk_tensors
from algorithms.env_tensor import EnvTensor


def _req(params: dict, key: str) -> float:
    """权重必须来自 config.yaml 显式给定；缺键报错，禁止静默落到默认 regime。"""
    if key not in params:
        raise KeyError(f"config.yaml params.{key} 缺失——权重类参数必须显式给定")
    return float(params[key])


def main() -> None:
    cfg = load_exp_config()
    exp = cfg.get("experiment", {})
    params = cfg.get("params", {})
    print("=" * 72)
    print(f"{exp.get('name')} — {exp.get('description')}")
    print("=" * 72)

    # 1) 网格
    grid = get_macro_grid() if params.get("grid", "macro") == "macro" else get_micro_grid()
    print("\n[Grid]")
    print(grid.summary())

    # 2) 数据
    data_type = (cfg.get("data") or {}).get("type", "real")
    t0 = _time.time()
    pr = load_experiment_data(grid, data_type, params, cfg.get("rain_environment"))
    print(f"[Data] done in {_time.time()-t0:.1f}s")

    # 3) 风险张量
    out_dir = RESULT_DIR
    out_dir.mkdir(exist_ok=True)
    resolved_path = out_dir / "_resolved_config.yaml"
    import yaml
    resolved_path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    risk = build_risk_tensors(
        pr, grid,
        flight_altitude=params.get("flight_altitude", 60.0),
        config_path=resolved_path,
    )
    print(f"\n[Risk] tensors built; p_crash range=[{risk['p_crash'].min():.3e}, "
          f"{risk['p_crash'].max():.3e}]")

    # 4) 规划（示例：同一 OD 多出发时刻；按实验改写）
    od = params["od"]
    hours = params["departure_hours"]
    planner_cfg = {
        "uav_speed": float(params.get("uav_speed", 10.0)),
        "w_distance": _req(params, "w_ops"),
        "w_fatality": _req(params, "w_fatal"),
        "w_property": _req(params, "w_prop"),
        "w_noise": _req(params, "w_noise"),
    }
    env = EnvTensor(
        p_crash=risk["p_crash"], fatality=risk["fatality"],
        property=risk["property"], noise=risk["noise"], grid=grid,
    )
    results = []
    for h in hours:
        res = plan_one(grid, env, planner_cfg, od, grid.get_time_index(h))
        results.append(res)
        print(f"  {h:02d}:00  {res.get('status')}  L={res.get('total_distance', float('nan')):.1f}")

    # 5) 可视化（全部在 plot/）
    plot_fig1(grid, risk["p_crash"], results, hours,
              params.get("z_layer", 5), od, out_dir / "fig1.png")

    # 6) 指标导出
    write_csv(out_dir / "metrics.csv", metrics_rows(hours, results))
    print(f"\n[Done] outputs -> {out_dir}")


if __name__ == "__main__":
    main()
