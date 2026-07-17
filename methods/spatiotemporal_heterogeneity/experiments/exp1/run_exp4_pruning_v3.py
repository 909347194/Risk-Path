"""
Experiment 4 v3: Label-Setting Pruning Efficiency

=== 核心改进设计 ===

问题根因：Exp4 v2 中风/雨热点不随时间变化 → 同一位置到达早晚风险相同
         → 标签被单调支配 → Label-Setting 无额外收益

改进策略：注入**强时间窗口风暴**
- 风暴中心在地图中央，仅在 t=10~14（10:00-14:00）活跃
- 风速 15 m/s（超过 V_limit=12 → P_crash→1）
- 14:00 后风暴消散，风险恢复正常

这创造了真正的时间-风险权衡：
- 路径 A（直穿）：到达风暴中心时恰好在窗口内 → 高风险
- 路径 B（绕行）：绕过风暴中心 → 低风险但更远
- 路径 C（等待/延迟）：在风暴前暂停，风暴后通过 → 需要时间标签支持

Label-Setting 的价值：
- 同一中间位置 P 可以通过不同路径在不同时刻到达
- 标签 L₁=(t₁, H₁, J₁) 和 L₂=(t₂, H₂, J₂) 可能互不支配
- 保留所有非支配标签 → 找到真正的全局最优
- 仅保留最佳标签（k=1）→ 可能剪掉全局最优路径
"""

from __future__ import annotations
import sys, time
from pathlib import Path
from typing import List, Tuple
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
MODULE = Path(__file__).resolve().parents[2]
if str(MODULE) not in sys.path:
    sys.path.insert(0, str(MODULE))

from src.tensor_engine.grid_system import GridSystem, SpatialGridConfig, TemporalGridConfig
from src.tensor_engine.dynamic_p_crash import DynamicCrashProbability
from src.tensor_engine.dynamic_fatality import DynamicFatalityModel
from src.tensor_engine.static_obstacle import PropertyDamageModel
from src.tensor_engine.dynamic_noise import DynamicNoiseCost
from src.algorithms.env_tensor import EnvTensor
from src.algorithms.a_star.astar_4d import AStar4D
from utils.synthetic_data_factory import generate_synthetic_city

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "exp4_pruning_v3"


def build_storm_scenario(seed=42):
    """
    构建风暴场景：100×100×12×48（50m分辨率，30min/步，24h）。

    关键设计：
    - 风暴中心 (50,50)，半径 15 格
    - 风暴窗口：t=20~28（对应 10:00-14:00，30min/步）
    - 窗口内风速 +15 m/s → P_crash 接近 1
    - 窗口外风速正常（0.5 m/s）
    - 无雨（隔离风场效应）
    """
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=100, ny=100, nz=12, dx=50.0, dy=50.0, dz=10.0),
        temporal=TemporalGridConfig(nt=48, dt_minutes=30.0),
    )
    nx, ny, nz, nt = grid.shape
    print(f"  Grid: {nx}×{ny}×{nz}×{nt} = {nx*ny*nz*nt:,} cells")
    print(f"  Time: {nt} steps × 30min = {nt*0.5:.0f}h")

    city = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=seed)
    landuse = city["landuse"].astype(np.int32)

    # === 注入风暴 ===
    wind_field = np.ones((ny, nx, nz, nt), dtype=np.float32) * 0.5  # 基础风速
    rain_data = np.zeros((ny, nx, nt), dtype=np.float32)

    # 风暴中心
    storm_cy, storm_cx = ny // 2, nx // 2  # (50, 50)
    storm_radius = 15  # 格
    yy, xx = np.mgrid[0:ny, 0:nx]
    dist_sq = (xx - storm_cx) ** 2 + (yy - storm_cy) ** 2
    storm_mask = np.exp(-dist_sq / (2 * storm_radius ** 2))  # 高斯衰减

    # 风暴窗口：t=20~28（10:00-14:00）
    STORM_START = 20
    STORM_END = 28
    STORM_WIND = 15.0  # m/s，超过 V_limit=12

    for t in range(nt):
        if STORM_START <= t < STORM_END:
            # 风暴活跃期：中心风速 +15 m/s
            for iz in range(nz):
                wind_field[:, :, iz, t] += storm_mask * STORM_WIND
            # 风暴期间也有降雨
            rain_data[:, :, t] += storm_mask * 8.0  # 8 mm/h

    # 人口潮汐（简化：夜间住宅区密集）
    lu_t = np.transpose(landuse, (1, 0))
    bp = np.transpose(city["population"].astype(np.float32), (1, 0))
    rp = np.zeros((nx, ny, nt), dtype=np.float32)
    for t in range(nt):
        hr = t * 0.5  # 30min steps
        p = bp.copy()
        if 8 <= hr <= 18:
            p[lu_t == 2] *= 5.0
        else:
            p[lu_t == 2] *= 0.1
        if 22 <= hr or hr <= 6:
            p[lu_t == 1] *= 4.0
        elif 9 <= hr <= 17:
            p[lu_t == 1] *= 0.2
        rp[:, :, t] = p

    return {
        "grid": grid,
        "landuse": landuse,
        "building_heights": city["building_heights"].astype(np.float32),
        "population": city["population"].astype(np.float32),
        "wind_field": wind_field,
        "rain_data": rain_data,
        "rho_pop": rp,
        "storm_info": {
            "center": (storm_cx, storm_cy),
            "radius": storm_radius,
            "window": (STORM_START, STORM_END),
            "wind_speed": STORM_WIND,
        },
    }


def build_env_tensor(sc, alt=50.0):
    """构建环境张量。"""
    grid = sc["grid"]
    nx, ny, nz, nt = grid.shape
    lu = sc["landuse"]

    cm = DynamicCrashProbability()
    w2d = np.transpose(sc["wind_field"][:, :, 0, :], (1, 0, 2))
    r2d = np.transpose(sc["rain_data"], (1, 0, 2))

    fw = cm.compute_wind_factor(w2d[:, :, np.newaxis, :])
    fr = cm.compute_rain_factor(r2d[:, :, np.newaxis, :])
    fo = np.ones((nx, ny, nz, nt), dtype=np.float32)
    pc = np.clip(cm.compute_pcrash(fw, fr, fo, dt=grid.temporal.dt_minutes * 60.0), 0, 1).astype(np.float32)

    rp = sc["rho_pop"]
    rv = rp * 0.1

    fm = DynamicFatalityModel()
    ef3d = fm.compute_fatality_consequence(rho_pop=rp, rho_vehicle=rv, flight_altitude=alt)
    ef = np.broadcast_to(ef3d[:, :, np.newaxis, :], (nx, ny, nz, nt)).astype(np.float32)

    bt = np.transpose(sc["building_heights"], (1, 0))
    pm = PropertyDamageModel(building_heights=bt, max_prop_damage=1000.0, log_normal_mu=3.04, log_normal_sigma=0.5)
    ep = pm.compute_property_consequence(flight_altitude=alt).astype(np.float32)

    nm = DynamicNoiseCost(grid=grid)
    lu_t = np.transpose(lu, (1, 0))
    rn = nm.compute_noise_cost(landuse=lu_t, population_density=rp).astype(np.float32)

    obs = np.zeros((nx, ny, nz), dtype=np.float32)
    for iz in range(nz):
        obs[:, :, iz] = (bt >= (iz + 1.0) * grid.spatial.dz).astype(np.float32)

    return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=grid)


def get_od_pairs_around_storm(grid, storm_info):
    """
    设计 OD 对使路径必须经过风暴区域附近。

    关键：OD 对的最短路径穿过风暴中心 → 算法必须选择绕行或直穿。
    """
    nx, ny = grid.spatial.nx, grid.spatial.ny
    cx, cy = storm_info["center"]

    return [
        {
            "name": "through_storm",
            "start": (10, 50, 5, 0),   # 西侧，y=风暴中心
            "goal": (89, 50, 5),         # 东侧，y=风暴中心
            "desc": "W→E 直穿风暴中心",
            "depart_time": 0,            # 出发时刻 0（凌晨）
        },
        {
            "name": "through_storm_t18",
            "start": (10, 50, 5, 18),   # 出发时 9:00，到达中心约 10:30（风暴窗口内）
            "goal": (89, 50, 5),
            "desc": "W→E 风暴窗口前出发",
            "depart_time": 18,
        },
        {
            "name": "through_storm_t30",
            "start": (10, 50, 5, 30),   # 出发时 15:00，到达中心约 16:30（风暴已过）
            "goal": (89, 50, 5),
            "desc": "W→E 风暴后出发",
            "depart_time": 30,
        },
        {
            "name": "diagonal",
            "start": (10, 10, 5, 18),   # SW，风暴前出发
            "goal": (89, 89, 5),
            "desc": "SW→NE 对角线穿越风暴",
            "depart_time": 18,
        },
    ]


def run_single(grid, env_tensor, od, max_labels):
    """执行单次搜索。"""
    config = {
        "uav_speed": 15.0,
        "w_distance": 0.40,
        "w_fatality": 0.30,
        "w_property": 0.15,
        "w_noise": 0.15,
        "survival_threshold": 0.01,
        "max_battery_time": float("inf"),
        "max_iterations": 10_000_000,
        "max_labels_per_cell": max_labels,
        "max_climb_rate": 5.0,
        "max_descent_rate": 5.0,
    }
    planner = AStar4D(grid, env_tensor, config)
    t0 = time.time()
    result = planner.search(od["start"], od["goal"])
    dt = (time.time() - t0) * 1000

    return {
        "od": od["name"],
        "k": max_labels,
        "status": result["status"],
        "path_length": result.get("total_distance", float("inf")),
        "objective_cost": result.get("objective_cost", float("inf")),
        "runtime_ms": dt,
        "nodes_explored": result.get("nodes_explored", 0),
        "final_survival": result.get("final_p_survival", 0.0),
        "cum_fatality": result.get("cum_fatality", 0.0),
        "cum_noise": result.get("cum_noise", 0.0),
    }


def run_experiment():
    print("=" * 60)
    print("Exp4 v3: Label-Setting with Time-Window Storm")
    print("=" * 60)

    # ===== 1. 构建风暴场景 =====
    print("\n[1/4] Building storm scenario...")
    sc = build_storm_scenario()
    grid = sc["grid"]
    si = sc["storm_info"]
    print(f"  Storm center: {si['center']}, radius: {si['radius']} cells")
    print(f"  Storm window: t={si['window'][0]}~{si['window'][1]} "
          f"({si['window'][0]*0.5:.0f}:00~{si['window'][1]*0.5:.0f}:00)")
    print(f"  Storm wind: {si['wind_speed']} m/s (V_limit=12)")

    # ===== 2. 构建风险张量 =====
    print("\n[2/4] Building risk tensor...")
    et = build_env_tensor(sc)
    print(f"  EnvTensor: {et.shape}")
    print(f"  P_crash range: [{et.p_crash.min():.6f}, {et.p_crash.max():.6f}]")

    # 验证风暴效果
    cx, cy = si["center"]
    t_storm = 24  # 12:00，风暴窗口内
    t_calm = 0    # 00:00，无风暴
    print(f"  P_crash at storm center, t={t_storm}: {et.p_crash[cx, cy, 5, t_storm]:.6f}")
    print(f"  P_crash at storm center, t={t_calm}: {et.p_crash[cx, cy, 5, t_calm]:.6f}")

    # ===== 3. 消融实验 =====
    ods = get_od_pairs_around_storm(grid, si)
    k_values = [1, 2, 4, 8, 16, 32, 64, 128]

    print(f"\n[3/4] Running ablation ({len(ods)} ODs × {len(k_values)} k-values)...")
    all_lines = ["od,k,status,path_length,objective_cost,runtime_ms,nodes_explored,final_survival,cum_fatality"]
    baseline = {}  # od_name -> (cost, path_length, survival)

    for od in ods:
        print(f"\n  === {od['name']}: {od['desc']} (depart t={od['depart_time']}) ===")

        # 先跑 baseline (k=128)
        bl = run_single(grid, et, od, 128)
        baseline[od["name"]] = bl
        if bl["status"] == "success":
            print(f"    Baseline k=128: dist={bl['path_length']:.1f}m  J={bl['objective_cost']:.4f}  "
                  f"surv={bl['final_survival']:.6f}  time={bl['runtime_ms']:.0f}ms  nodes={bl['nodes_explored']}")
        else:
            print(f"    Baseline k=128: FAILED ({bl.get('reason','?')})")

        # 消融
        for k in k_values:
            r = run_single(grid, et, od, k)
            gap = ""
            if r["status"] == "success" and bl["status"] == "success" and bl["objective_cost"] > 0:
                pct = (r["objective_cost"] - bl["objective_cost"]) / bl["objective_cost"] * 100
                gap = f"  gap={pct:+.2f}%"
                if abs(pct) < 0.01:
                    gap += " ✓"
                elif pct > 0.01:
                    gap += " ← SUBOPTIMAL"

            status_str = f"dist={r['path_length']:.1f}m J={r['objective_cost']:.4f} surv={r['final_survival']:.6f}" if r["status"] == "success" else r["status"]
            print(f"    k={k:3d}: {status_str}  time={r['runtime_ms']:.0f}ms  nodes={r['nodes_explored']}{gap}")

            all_lines.append(f"{od['name']},{k},{r['status']},{r['path_length']:.4f},"
                             f"{r['objective_cost']:.6f},{r['runtime_ms']:.1f},{r['nodes_explored']},"
                             f"{r['final_survival']:.6f},{r['cum_fatality']:.8f}")

    # ===== 4. 保存结果 =====
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "ablation_labels.csv"
    csv_path.write_text("\n".join(all_lines), encoding="utf-8")
    print(f"\n[4/4] Saved: {csv_path}")

    # ===== 分析总结 =====
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    suboptimal_found = False
    for od in ods:
        bl = baseline[od["name"]]
        print(f"\n  {od['name']} ({od['desc']}):")
        for k in k_values:
            r = run_single(grid, et, od, k)
            if r["status"] == "success" and bl["status"] == "success" and bl["objective_cost"] > 0:
                pct = (r["objective_cost"] - bl["objective_cost"]) / bl["objective_cost"] * 100
                marker = "✓ optimal" if abs(pct) < 0.01 else f"SUBOPTIMAL (+{pct:.2f}%)"
                if abs(pct) >= 0.01:
                    suboptimal_found = True
            else:
                marker = r["status"]
            print(f"    k={k:3d}: J={r['objective_cost']:.4f}  nodes={r['nodes_explored']}  {marker}")

    print("\n  " + "=" * 40)
    if suboptimal_found:
        print("  ✅ Label-Setting pruning impact demonstrated!")
        print("  Small k values lead to suboptimal paths.")
        print("  The Pareto dominance mechanism preserves optimality.")
    else:
        print("  ⚠️  All k values found same optimal path.")
        print("  The search space may not have enough label conflicts.")
        print("  Consider: stronger storm, larger grid, or more OD pairs.")

    return all_lines


if __name__ == "__main__":
    run_experiment()
