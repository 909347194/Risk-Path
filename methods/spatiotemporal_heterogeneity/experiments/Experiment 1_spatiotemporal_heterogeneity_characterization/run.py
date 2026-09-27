#!/usr/bin/env python3
"""
Exp 1 — 时空异质性表征 (Spatiotemporal Heterogeneity Characterization)
=========================================================================

目的
----
回答论文证据链的第一个问题：**风险场是否明显随空间和时间同时变化？**

    Cost(x,y,z,t) = P_crash(x,y,z,t) · [fatality + property] + noise

其中
- P_crash 受 风(V_ref(t)·F_z(z)·F_urban(x,y))、城市峡谷(SVF(x,y)) 驱动；
- fatality / noise 受人口潮汐 ρ_pop(x,y,t) 与用地类型驱动（昼夜节律）。

因此同一城市、同一 OD，在不同出发时刻面对的是**不同的风险场**，
最优路径也应随之改变。

数据源
------
真实数据（data/02_processed 顶层「已准备好」的数组，**只读加载**），
宏观网格 100×100×12（dx=48.459 m, dy=47.936 m），96 时相 × 15 min。
降雨暂不考虑（暂无真实降雨数据），rain_data 置零。
注意：刻意绕过 DataPipeline(real).run_all() —— 该管线会从 01_raw 重算并
覆盖已提交数据（实测相对差 50%–90%）。

做法
----
1. DataPipeline(data_type='real') 组装 landuse / building / 人口潮汐 / POI；
2. build_risk_tensors 组装四维风险张量（含情景化风场 moderate）；
3. 在 08:00 / 12:00 / 18:00 / 22:00 四个出发时刻各跑一次 TD-RiskA*
   （60 m 定高巡航，风险规避权重）；
4. 输出 Figure 1（四时刻风险场 + 同 OD 路径）、Figure 2（风/人口驱动因子）、
   Figure 3（四路径叠加对比 + 指标柱状图），并导出量化指标。

运行：python3 run.py
产物：result/fig1_risk_field.png, fig2_drivers.png, fig3_path_comparison.png,
      result/metrics.csv, result/heterogeneity.csv, result/path_difference.csv
"""
from __future__ import annotations

import copy
import sys
import time as _time
from itertools import combinations
from pathlib import Path

import numpy as np
import yaml

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---- 让 experiments/ 下的脚本能直接 import src 内的包 ----
HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE.parents[1]                      # spatiotemporal_heterogeneity/
sys.path.insert(0, str(MODULE_ROOT / "src"))

from tensor_engine.grid_system import get_macro_grid, get_micro_grid
from tensor_engine.risk_tensor_assembler import build_risk_tensors
from tensor_engine.wind_environment import get_wind_environment, _compute_svf
from data_provision.pipeline import DataPipeline, PipelineResult
from data_provision.paths import get_data_paths
from algorithms.env_tensor import EnvTensor
from algorithms.a_star.astar_4d import AStar4D


# --------------------------------------------------------------------------
# 配置：支持 extends 继承公共配置（实验值覆盖公共值）
# --------------------------------------------------------------------------
def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_exp_config(path: Path) -> dict:
    """读取实验配置；支持 `extends: <相对路径>` 继承公共配置。"""
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parent = cfg.pop("extends", None)
    if parent:
        base_path = (path.parent / parent).resolve()
        if base_path.exists():
            base = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}
            base.pop("extends", None)
            cfg = _deep_merge(base, cfg)
        else:
            print(f"⚠ extends 指向的文件不存在，跳过继承: {base_path}")
    return cfg


# --------------------------------------------------------------------------
# 真实数据：只读加载 data/02_processed 顶层已准备好的数组
# --------------------------------------------------------------------------
def load_prepared_real_data(grid) -> PipelineResult:
    """直接加载已准备好的真实数据（**只读，不重算、不回写**）。

    重要：DataPipeline(data_type='real').run_all() 会从 01_raw 原始数据重算
    并 **覆盖** data/02_processed 下的已提交数据（实测重算结果与提交版本
    相对差达 50%–90%，POI/人口全部不同）。本实验要用的正是「准备好的」
    数据，因此这里绕过 run_all，逐文件 np.load 只读加载。
    """
    paths = get_data_paths("real")          # data/02_processed（顶层）
    nx, ny, nz, nt = grid.shape

    def _load(p: Path, name: str):
        if not p.exists():
            raise FileNotFoundError(f"缺少真实数据文件: {p}")
        return np.load(p)

    landuse = _load(paths.landuse_map_path, "landuse")
    building = _load(paths.building_heights_path, "building_heights")
    road = _load(paths.road_mask_path, "road_mask")
    base_pop = _load(paths.base_pop_path, "base_pop")
    rho_pop = _load(paths.rho_pop_path, "rho_pop")
    rho_vehicle = _load(paths.rho_vehicle_path, "rho_vehicle")

    # poi_counts.npz：dict 结构（类别名 → (nx, ny)）
    poi_npz = _load(paths.poi_counts_path, "poi_counts")
    poi_counts = {k: poi_npz[k] for k in poi_npz.files if k != "categories"}

    # 形状校验：与宏观网格严格对齐，防止「数据-网格」错配悄悄污染风险场
    checks = {
        "landuse": (landuse, (nx, ny)),
        "building_heights": (building, (nx, ny)),
        "road_mask": (road, (nx, ny)),
        "base_pop": (base_pop, (nx, ny)),
        "rho_pop": (rho_pop, (nx, ny, nt)),
        "rho_vehicle": (rho_vehicle, (nx, ny, nt)),
    }
    for name, (arr, expect) in checks.items():
        if tuple(arr.shape) != expect:
            raise ValueError(
                f"真实数据 {name} 形状 {arr.shape} 与网格 {expect} 不符；"
                "请检查 spatial_grid 配置与 data/02_processed 数据版本。"
            )
    for k, v in poi_counts.items():
        if tuple(v.shape) != (nx, ny):
            raise ValueError(f"POI {k} 形状 {v.shape} 与网格 {(nx, ny)} 不符")

    print(f"[Data] 只读加载已准备真实数据: {paths.processed}")
    print(f"  landuse{landuse.shape}  building{building.shape}  "
          f"rho_pop{rho_pop.shape}  poi×{len(poi_counts)}")
    return PipelineResult(
        landuse=landuse,
        building_heights=building,
        road_mask=road,
        base_population=base_pop,
        poi_counts=poi_counts,
        rho_population=rho_pop,
        rho_vehicle=rho_vehicle,
        wind_field=None,          # 风场走情景化模型（scenario mode）
        rain_data=None,           # 降雨暂不考虑，由 build_rain 填充
        paths=paths,
    )


# --------------------------------------------------------------------------
# 降雨：Exp 1 不考虑（暂无真实降雨数据）。保留开关，接入后即可启用。
# --------------------------------------------------------------------------
def build_rain(grid, params: dict) -> np.ndarray:
    """降雨强度场 (nx, ny, nt)，单位 mm/h。

    默认关闭：Exp 1 只做「风 + 城市形态 + 人口潮汐」驱动的时空异质性表征。
    若后续接入真实降雨（或需要情景化降雨热点），把 config 中
    params.rain.enabled 置 true 并给定 center / radius / intensity_mmh /
    active_hours 即可，无需改代码。
    """
    nx, ny, nz, nt = grid.shape
    rcfg = (params.get("rain") or {})
    if not rcfg.get("enabled", False):
        return np.zeros((nx, ny, nt), dtype=np.float32)

    cx, cy = rcfg.get("center", [nx // 2, ny // 2])
    r = float(rcfg.get("radius", 10))
    I = float(rcfg.get("intensity_mmh", 10.0))
    h0, h1 = rcfg.get("active_hours", [14, 20])
    t0, t1 = grid.get_time_index(h0), grid.get_time_index(h1)

    yy, xx = np.mgrid[0:ny, 0:nx]
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    spatial = (dist <= r).astype(np.float32) * I
    rain = np.zeros((nx, ny, nt), dtype=np.float32)
    rain[:, :, t0:t1 + 1] = spatial[:, :, None]
    return rain


# --------------------------------------------------------------------------
# 路径规划：同一 OD、给定出发时刻（60 m 定高巡航）
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# 可视化
# --------------------------------------------------------------------------
def plot_fig1(grid, p_crash, results, hours, z_layer, od, out_path):
    """Figure 1：四时刻风险场（P_crash）+ 同一 OD 的规划路径。"""
    vmax = float(np.percentile(p_crash[:, :, z_layer, :], 99))
    vmax = max(vmax, 1e-6)

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 11.5), layout="constrained")
    fig.suptitle(
        "Figure 1 — Spatiotemporal risk field $P_{crash}(x,y,z,t)$ and optimal path\n"
        f"same OD ({od[0]},{od[1]}) -> ({od[3]},{od[4]}) at z≈{(z_layer+1)*grid.spatial.dz:.0f} m; "
        "different departure time -> different risk landscape -> different path",
        fontsize=13,
    )
    im = None
    for ax, h, res in zip(axes.flat, hours, results):
        t_idx = grid.get_time_index(h)
        im = ax.imshow(p_crash[:, :, z_layer, t_idx].T, origin="lower",
                       cmap="inferno", vmin=0, vmax=vmax)
        xs, ys = path_xy(res)
        if xs:
            ax.plot(xs, ys, color="cyan", lw=2.0,
                    label=f"path L={res['total_distance']:.0f} m")
            ax.plot(xs[0], ys[0], "o", color="lime", ms=9, label="start")
            ax.plot(xs[-1], ys[-1], "*", color="red", ms=13, label="goal")
        ok = res.get("status") == "success"
        ax.set_title(
            f"{h:02d}:00  $P_{{surv}}$={res.get('final_p_survival', float('nan')):.4f}"
            if ok else f"{h:02d}:00  (failed: {res.get('reason')})", fontsize=11)
        ax.set_xlabel("x (grid)")
        ax.set_ylabel("y (grid)")
        if xs:
            ax.legend(loc="upper right", fontsize=8, framealpha=0.85)
    if im is not None:
        cbar = fig.colorbar(im, ax=axes, shrink=0.85, pad=0.02)
        cbar.set_label("$P_{crash}$")
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_fig2(grid, wind_4d, rho_pop, hours, z_layer, out_path):
    """Figure 2：驱动因子 —— 风场（上排）与人口密度（下排）在 4 个时刻的演化。"""
    wmax = float(np.percentile(wind_4d[:, :, z_layer, :], 99)) or 1.0
    pmax = float(np.percentile(rho_pop, 99)) or 1.0

    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5), layout="constrained")
    fig.suptitle("Figure 2 — Drivers of spatiotemporal heterogeneity: "
                 "wind speed & population density", fontsize=13)
    for j, h in enumerate(hours):
        t_idx = grid.get_time_index(h)
        imw = axes[0, j].imshow(wind_4d[:, :, z_layer, t_idx].T, origin="lower",
                                cmap="viridis", vmin=0, vmax=wmax)
        axes[0, j].set_title(f"wind @ {h:02d}:00")
        # 人口热点位置标注（直观展示昼夜潮汐位移）
        slab = rho_pop[:, :, t_idx]
        px, py = np.unravel_index(np.argmax(slab), slab.shape)
        imp = axes[1, j].imshow(slab.T, origin="lower", cmap="YlOrRd", vmin=0, vmax=pmax)
        axes[1, j].plot(px, py, "b*", ms=11)
        axes[1, j].set_title(f"population @ {h:02d}:00\npeak at ({px},{py})")
        for i in (0, 1):
            axes[i, j].set_xlabel("x (grid)")
            axes[i, j].set_ylabel("y (grid)")
    fig.colorbar(imw, ax=axes[0, :], shrink=0.85, pad=0.02, label="m/s")
    fig.colorbar(imp, ax=axes[1, :], shrink=0.85, pad=0.02, label="density")
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_fig3(grid, results, hours, building, od, out_path):
    """Figure 3：四条路径叠加对比 + 路径长度 / 存活率 柱状图。"""
    fig = plt.figure(figsize=(16.5, 5.6), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1.35, 1.0, 1.0])

    # (a) 四条路径叠加（背景：建筑高度，静态城市底图）
    ax0 = fig.add_subplot(gs[0, 0])
    b_vmax = float(np.percentile(building, 98)) or float(building.max()) or 1.0
    ax0.imshow(building.T, origin="lower", cmap="Greys",
               vmin=0, vmax=b_vmax, interpolation="nearest")
    colors = ["cyan", "orange", "lime", "magenta"]
    for h, res, c in zip(hours, results, colors):
        xs, ys = path_xy(res)
        if xs:
            ax0.plot(xs, ys, color=c, lw=2.2, label=f"{h:02d}:00  L={res['total_distance']:.0f} m")
    ax0.plot(od[0], od[1], "o", color="white", ms=10, mec="k", label="start")
    ax0.plot(od[3], od[4], "*", color="yellow", ms=15, mec="k", label="goal")
    ax0.set_title("(a) Planned paths for the same OD, 4 departure times")
    ax0.set_xlabel("x (grid)")
    ax0.set_ylabel("y (grid)")
    ax0.legend(loc="upper left", fontsize=8, framealpha=0.9)

    ok = [r for r in results if r.get("status") == "success"]
    ok_hours = [h for h, r in zip(hours, results) if r.get("status") == "success"]

    # (b) 路径长度
    ax1 = fig.add_subplot(gs[0, 1])
    L = [r["total_distance"] for r in ok]
    bars = ax1.bar([f"{h:02d}:00" for h in ok_hours], L, color="steelblue")
    ax1.set_title("(b) Path length vs departure time")
    ax1.set_ylabel("path length (m)")
    ax1.set_ylim(min(L) * 0.92 if L else 0, max(L) * 1.04 if L else 1)
    ax1.bar_label(bars, fmt="%.0f", fontsize=8)
    if L:
        ax1.axhline(min(L), ls="--", c="k", lw=1,
                    label=f"min {min(L):.0f} m")
        ax1.legend(fontsize=8)

    # (c) 存活率
    ax2 = fig.add_subplot(gs[0, 2])
    P = [r["final_p_survival"] for r in ok]
    bars2 = ax2.bar([f"{h:02d}:00" for h in ok_hours], P, color="indianred")
    ax2.set_title("(c) Survival probability vs departure time")
    ax2.set_ylabel("$P_{surv}$")
    ax2.set_ylim(0, max(P) * 1.25 if P else 1)
    ax2.bar_label(bars2, fmt="%.4f", fontsize=8)

    fig.suptitle("Figure 3 — Same OD, different departure time -> different optimal path",
                 fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


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


def plot_fig4(rows, hours, out_path):
    """Figure 4：权重敏感性 —— 三种 regime 与「路径随时刻变化」的稳健性。"""
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), layout="constrained")
    ratios = [r["ratio"] for r in rows]
    spread = [r["spread_m"] for r in rows]

    ax0 = axes[0]
    ax0.plot(ratios, spread, "o-", color="darkslateblue", lw=2)
    for x, y in zip(ratios, spread):
        ax0.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=8)
    ax0.set_xlabel("risk aversion  $w_{fatal}/w_{ops}$")
    ax0.set_ylabel("path length spread across departure times (m)")
    ax0.set_title("(a) Spread vs risk aversion (three regimes)")
    ax0.grid(alpha=0.3)

    ax1 = axes[1]
    markers = ["o", "s", "^", "D", "v"]
    for i, r in enumerate(rows):
        ax1.plot(hours, [r[f"L_{h:02d}h"] for h in hours], marker=markers[i % len(markers)],
                 lw=1.8, label=f"ratio={r['ratio']:.0f} (spread {r['spread_m']:.0f} m)")
    ax1.set_xlabel("departure hour")
    ax1.set_ylabel("path length (m)")
    ax1.set_title("(b) Path length vs departure hour, per risk aversion")
    ax1.set_xticks(hours)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    fig.suptitle("Figure 4 — Weight sensitivity: path response to departure time "
                 "is regime-dependent (not a single cherry-picked weight)", fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)


# --------------------------------------------------------------------------
# 异质性量化
# --------------------------------------------------------------------------
def heterogeneity_stats(p_crash, z_layer, hours, grid):
    """量化风险场在给定高度层上的空间异质性与时间异质性。"""
    slabs = np.stack([p_crash[:, :, z_layer, grid.get_time_index(h)] for h in hours])
    spatial_cv = [float(s.std() / s.mean()) if s.mean() > 0 else 0.0 for s in slabs]
    # 时间维：逐格点跨出发时刻的变异系数，取中位数（对离群稳健）
    per_cell_cv = slabs.std(axis=0) / np.maximum(slabs.mean(axis=0), 1e-12)
    temporal_cv_median = float(np.median(per_cell_cv))
    # 时间维：逐格点跨出发时刻的相对极差（max-min)/mean 的中位数
    rng = (slabs.max(axis=0) - slabs.min(axis=0)) / np.maximum(slabs.mean(axis=0), 1e-12)
    temporal_range_median = float(np.median(rng))
    return {
        "spatial_cv_per_hour": {h: round(v, 4) for h, v in zip(hours, spatial_cv)},
        "temporal_cv_median": round(temporal_cv_median, 4),
        "temporal_relative_range_median": round(temporal_range_median, 4),
    }


def _to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(rows[0].keys())
    lines = [",".join(cols)]
    for r in rows:
        lines.append(",".join(str(r.get(c, "")) for c in cols))
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main() -> None:
    cfg = load_exp_config(HERE / "config.yaml")
    exp = cfg.get("experiment", {})
    params = cfg.get("params", {})
    print("=" * 72)
    print(f"Exp 1: {exp.get('name')} — {exp.get('description')}")
    print("=" * 72)

    # 1) 网格：真实数据 → 宏观网格（精确分辨率 48.459 × 47.936 m）
    if params.get("grid", "macro") == "macro":
        grid = get_macro_grid()
    else:
        grid = get_micro_grid()
    print("\n[Grid]")
    print(grid.summary())

    # 2) 数据：真实数据只读加载（synthetic 才走 DataPipeline）
    data_type = (cfg.get("data") or {}).get("type", "real")
    t0 = _time.time()
    if data_type == "real":
        pr = load_prepared_real_data(grid)
    else:
        pr = DataPipeline(data_type=data_type).run_all(skip_weather=True)
    pr.rain_data = build_rain(grid, params)
    print(f"[Data] done in {_time.time()-t0:.1f}s; "
          f"rain enabled={bool((params.get('rain') or {}).get('enabled', False))}")

    # 3) 组装四维风险张量（情景化风场，继承 common.yaml wind_environment）
    #    把「实验配置 + 公共配置」合并后落盘，保证 build_risk_tensors 拿到完整参数。
    resolved = load_exp_config(HERE / "config.yaml")
    out_dir = HERE / "result"
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

    # 5) 路径规划：同一 OD、四个出发时刻（60 m 定高巡航）
    od = params["od"]
    hours = params["departure_hours"]
    z_layer = params.get("z_layer", 5)
    alt = (z_layer + 1.0) * grid.spatial.dz          # 层中心物理高度

    planner_cfg = {
        "uav_speed": float(params.get("uav_speed", 10.0)),
        "w_distance": float(params.get("w_ops", 0.03)),
        "w_fatality": float(params.get("w_fatal", 6.0)),
        "w_property": float(params.get("w_prop", 2.4)),
        "w_noise": float(params.get("w_noise", 1.5)),
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
    print("\n[Planning] same OD, 4 departure times (cruise alt "
          f"{alt:.0f} m, w_risk/w_ops={params.get('w_fatal',6.0)/params.get('w_ops',0.03):.0f})")
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

    # 6) 可视化
    plot_fig1(grid, risk["p_crash"], results, hours, z_layer, od, out_dir / "fig1_risk_field.png")
    plot_fig2(grid, wind_4d, pr.rho_population, hours, z_layer, out_dir / "fig2_drivers.png")
    plot_fig3(grid, results, hours, pr.building_heights, od, out_dir / "fig3_path_comparison.png")
    print(f"\n[Figures] {out_dir}/fig1_risk_field.png, fig2_drivers.png, fig3_path_comparison.png")

    # 7) 指标导出
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
    (out_dir / "metrics.csv").write_text(_to_csv(rows), encoding="utf-8")

    # 8) 路径差异量化（两两对比，证明「路径确实随出发时刻改变」）
    diff_rows = []
    cells = {h: path_cells_m(r, grid) for h, r in zip(hours, results)
             if r.get("status") == "success"}
    for h1, h2 in combinations(sorted(cells), 2):
        diff_rows.append({
            "departure_hour_a": h1,
            "departure_hour_b": h2,
            "length_diff_m": round(abs(
                rows[[r["departure_hour"] for r in rows].index(h1)]["path_length_m"]
                - rows[[r["departure_hour"] for r in rows].index(h2)]["path_length_m"]), 3),
            "mean_deviation_m": round(mean_deviation_m(cells[h1], cells[h2]), 3),
        })
    if diff_rows:
        (out_dir / "path_difference.csv").write_text(_to_csv(diff_rows), encoding="utf-8")

    # 9) 异质性统计
    het = heterogeneity_stats(risk["p_crash"], z_layer, hours, grid)
    het_rows = [{"metric": k, "value": v} for k, v in het.items()]
    het_rows.append({"metric": "spatial_cv_per_hour(detail)", "value": ""})
    for h, v in het["spatial_cv_per_hour"].items():
        het_rows.append({"metric": f"  spatial_cv_{h:02d}h", "value": v})
    (out_dir / "heterogeneity.csv").write_text(_to_csv(het_rows), encoding="utf-8")

    print(f"[Metrics] {out_dir}/metrics.csv, path_difference.csv, heterogeneity.csv")
    print("\n[Heterogeneity]")
    print(f"  spatial CV of P_crash per hour: {het['spatial_cv_per_hour']}")
    print(f"  temporal CV (median over cells): {het['temporal_cv_median']}")
    print(f"  temporal relative range (median): {het['temporal_relative_range_median']}")

    # 9b) 权重敏感性扫描（证明「路径随出发时刻变化」不是挑参数挑出来的）
    sens = (params.get("sensitivity") or {})
    if sens.get("enabled", False):
        wf_list = sens.get("w_fatal_values") or [params.get("w_fatal", 30.0)]
        print(f"\n[Sensitivity] sweeping w_fatal {wf_list}")
        sens_rows = run_sensitivity(grid, env, planner_cfg, od, hours, wf_list)
        (out_dir / "sensitivity.csv").write_text(_to_csv(sens_rows), encoding="utf-8")
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
