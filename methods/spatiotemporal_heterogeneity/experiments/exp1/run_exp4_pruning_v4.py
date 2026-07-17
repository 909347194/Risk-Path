"""
Exp4 v4: Label-Setting — 基于"峡谷瓶颈"场景

=== 核心思路 ===

不是用"风暴绕行"（那只会产生唯一路径），而是设计一个**窄通道瓶颈**：

场景布局：
- 地图中央有一条**东西向的建筑墙**，只在中间留一个窄缺口
- 缺口处有**时间变化的风险**（风速在某些时段升高）
- 所有 W→E 的路径**必须经过缺口**
- 但可以在不同时间到达缺口：
  - 路径 A：快速到达缺口，但此时风速高 → 高 P_crash
  - 路径 B：绕路延迟到达缺口，风速已降 → 低 P_crash
  - 路径 C：在缺口前等待（hover），等风速降低

Label-Setting 的价值：
- 缺口前的某个位置 P，可以通过"快路径"在 t₁ 到达（H₁ 高），
  也可以通过"慢路径"在 t₂ 到达（H₂ 低）
- 标签 (t₁, H₁, J₁) 和 (t₂, H₂, J₂) 互不支配
- 保留两者 → 找到真正的全局最优
- 仅保留 k=1 → 可能剪掉最优标签

关键：风险不能太高（否则必须绕行），也不能太低（否则直穿最优）。
设置为"中等风险"——直穿存活率 ~50%，绕行存活率 ~90%。
"""
from __future__ import annotations
import sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
MODULE = Path(__file__).resolve().parents[2]
if str(MODULE) not in sys.path: sys.path.insert(0, str(MODULE))

from src.tensor_engine.grid_system import GridSystem, SpatialGridConfig, TemporalGridConfig
from src.tensor_engine.dynamic_p_crash import DynamicCrashProbability
from src.tensor_engine.dynamic_fatality import DynamicFatalityModel
from src.tensor_engine.static_obstacle import PropertyDamageModel
from src.tensor_engine.dynamic_noise import DynamicNoiseCost
from src.algorithms.env_tensor import EnvTensor
from src.algorithms.a_star.astar_4d import AStar4D
from utils.synthetic_data_factory import generate_synthetic_city

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "exp4_pruning_v4"


def build_canyon_scenario(seed=42):
    """
    构建峡谷瓶颈场景。

    布局（100×100 网格）：
    - y=45~55：建筑墙（障碍物），只在 x=45~55 留缺口
    - 缺口处：时间变化风速
      - t=0~24（0:00~12:00）：风速 6 m/s（中等，P_crash ~0.001）
      - t=24~36（12:00~18:00）：风速 11 m/s（高，接近 V_limit，P_crash ~0.05）
      - t=36~48（18:00~24:00）：风速 4 m/s（低，P_crash ~0.0001）
    - 无雨
    - OD：(5, 50) → (94, 50)，必须穿过缺口
    """
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=100, ny=100, nz=12, dx=50.0, dy=50.0, dz=10.0),
        temporal=TemporalGridConfig(nt=48, dt_minutes=30.0),
    )
    nx, ny, nz, nt = grid.shape
    print(f"  Grid: {nx}×{ny}×{nz}×{nt}")

    city = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=seed)

    # === 建筑墙 ===
    # 在 y=45~55, x≠[45,55] 处放置高建筑（障碍物）
    bh = city["building_heights"].astype(np.float32).copy()
    for y in range(45, 56):
        for x in range(nx):
            if not (45 <= x <= 55):  # 缺口在 x=45~55
                bh[y, x] = 40.0  # 4 层建筑 = 40m，覆盖 z=1~4，z=5(60m)可飞越

    # === 时间变化风场 ===
    wind_field = np.ones((ny, nx, nz, nt), dtype=np.float32) * 1.0  # 基础风速

    # 缺口区域的风速变化
    for t in range(nt):
        hr = t * 0.5  # 30min steps
        if 12.0 <= hr < 18.0:
            # 12:00-18:00：高风速
            wind_factor = 11.0
        elif 6.0 <= hr < 12.0:
            # 06:00-12:00：中等风速
            wind_factor = 6.0
        else:
            # 夜间/傍晚：低风速
            wind_factor = 3.0

        # 风速在缺口区域（x=40~60, y=42~58）增强
        for iz in range(nz):
            wind_field[42:58, 40:60, iz, t] += wind_factor

    rain_data = np.zeros((ny, nx, nt), dtype=np.float32)

    # 人口潮汐
    landuse = city["landuse"].astype(np.int32)
    lu_t = np.transpose(landuse, (1, 0))
    bp = np.transpose(city["population"].astype(np.float32), (1, 0))
    rp = np.zeros((nx, ny, nt), dtype=np.float32)
    for t in range(nt):
        hr = t * 0.5
        p = bp.copy()
        if 8 <= hr <= 18: p[lu_t == 2] *= 5.0
        else: p[lu_t == 2] *= 0.1
        if 22 <= hr or hr <= 6: p[lu_t == 1] *= 4.0
        elif 9 <= hr <= 17: p[lu_t == 1] *= 0.2
        rp[:, :, t] = p

    return {
        "grid": grid,
        "landuse": landuse,
        "building_heights": bh,
        "population": city["population"].astype(np.float32),
        "wind_field": wind_field,
        "rain_data": rain_data,
        "rho_pop": rp,
    }


def build_env_tensor(sc, alt=50.0):
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
        z_height = (iz + 1.0) * grid.spatial.dz
        obs[:, :, iz] = (bt >= z_height).astype(np.float32)

    return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=grid)


def run_single(grid, et, start, goal, max_labels):
    config = {
        "uav_speed": 15.0, "w_distance": 0.30, "w_fatality": 0.40,
        "w_property": 0.15, "w_noise": 0.15,
        "survival_threshold": 0.001,  # 放宽存活阈值，允许穿越风险区
        "max_battery_time": float("inf"), "max_iterations": 10_000_000,
        "max_labels_per_cell": max_labels,
        "max_climb_rate": 5.0, "max_descent_rate": 5.0,
    }
    planner = AStar4D(grid, et, config)
    t0 = time.time()
    result = planner.search(start, goal)
    dt = (time.time() - t0) * 1000
    return {
        "k": max_labels, "status": result["status"],
        "path_length": result.get("total_distance", float("inf")),
        "objective_cost": result.get("objective_cost", float("inf")),
        "runtime_ms": dt, "nodes_explored": result.get("nodes_explored", 0),
        "final_survival": result.get("final_p_survival", 0.0),
        "cum_fatality": result.get("cum_fatality", 0.0),
    }


def run_experiment():
    print("=" * 60)
    print("Exp4 v4: Canyon Bottleneck with Time-Varying Risk")
    print("=" * 60)

    print("\n[1/3] Building scenario...")
    sc = build_canyon_scenario()
    grid = sc["grid"]

    print("\n[2/3] Building risk tensor...")
    et = build_env_tensor(sc)
    print(f"  EnvTensor: {et.shape}")

    # 验证风险分布
    nx, ny, nz, nt = grid.shape
    # 缺口中心 (50,50) 在不同时刻的 P_crash
    for t_test, label in [(0, "00:00"), (12, "06:00"), (24, "12:00"), (36, "18:00"), (40, "20:00")]:
        pc = et.p_crash[50, 50, 5, t_test]
        wind = sc["wind_field"][50, 50, 0, t_test]
        print(f"  t={t_test:2d} ({label}): wind={wind:.1f} m/s, P_crash={pc:.6f}")

    # ===== 搜索实验 =====
    print("\n[3/3] Running searches...")

    # OD 对：必须穿过缺口
    ods = [
        {"name": "morning_calm", "start": (5, 50, 5, 0), "goal": (94, 50, 5),
         "desc": "凌晨出发，到达缺口时风速低"},
        {"name": "noon_risky", "start": (5, 50, 5, 12), "goal": (94, 50, 5),
         "desc": "上午出发，到达缺口时风速中等"},
        {"name": "afternoon_storm", "start": (5, 50, 5, 20), "goal": (94, 50, 5),
         "desc": "午后出发，到达缺口时风速最高"},
        {"name": "evening_safe", "start": (5, 50, 5, 36), "goal": (94, 50, 5),
         "desc": "傍晚出发，到达缺口时风速已降"},
    ]

    k_values = [1, 2, 4, 8, 16, 32, 64]
    lines = ["od,k,status,path_length,objective_cost,runtime_ms,nodes_explored,final_survival"]

    for od in ods:
        print(f"\n  === {od['name']}: {od['desc']} ===")

        # Baseline
        bl = run_single(grid, et, od["start"], od["goal"], 128)
        bl_cost = bl["objective_cost"] if bl["status"] == "success" else None

        if bl["status"] == "success":
            print(f"    Baseline k=128: dist={bl['path_length']:.1f}m J={bl['objective_cost']:.4f} "
                  f"surv={bl['final_survival']:.6f} time={bl['runtime_ms']:.0f}ms nodes={bl['nodes_explored']}")
        else:
            print(f"    Baseline k=128: FAILED")

        for k in k_values:
            r = run_single(grid, et, od["start"], od["goal"], k)
            gap = ""
            if r["status"] == "success" and bl_cost and bl_cost > 0:
                pct = (r["objective_cost"] - bl_cost) / bl_cost * 100
                if abs(pct) < 0.01: gap = " ✓"
                elif pct > 0.01: gap = f" ← +{pct:.2f}%"
                else: gap = f" ({pct:.2f}%)"

            st = f"dist={r['path_length']:.1f}m J={r['objective_cost']:.4f} surv={r['final_survival']:.6f}" if r["status"] == "success" else r["status"]
            print(f"    k={k:3d}: {st}  time={r['runtime_ms']:.0f}ms  nodes={r['nodes_explored']}{gap}")

            lines.append(f"{od['name']},{k},{r['status']},{r['path_length']:.4f},"
                         f"{r['objective_cost']:.6f},{r['runtime_ms']:.1f},{r['nodes_explored']},"
                         f"{r['final_survival']:.6f}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ablation_labels.csv").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nSaved: {OUTPUT_DIR / 'ablation_labels.csv'}")

    # ===== 扫描出发时刻，观察时间自适应 =====
    print("\n" + "=" * 60)
    print("TIME SCAN: t_depart = 0,2,4,...,46")
    print("=" * 60)
    scan_lines = ["t_depart,hour,status,path_length,objective_cost,runtime_ms,nodes_explored,final_survival"]
    for t_dep in range(0, 48, 2):
        start = (5, 50, 5, t_dep)
        goal = (94, 50, 5)
        r = run_single(grid, et, start, goal, 8)
        hr = t_dep * 0.5
        st = f"dist={r['path_length']:.0f}m J={r['objective_cost']:.3f} surv={r['final_survival']:.4f}" if r["status"] == "success" else r["status"]
        print(f"  t={t_dep:2d} ({hr:05.2f}h): {st}  nodes={r['nodes_explored']}  time={r['runtime_ms']:.0f}ms")
        scan_lines.append(f"{t_dep},{hr:.2f},{r['status']},{r['path_length']:.4f},"
                          f"{r['objective_cost']:.6f},{r['runtime_ms']:.1f},{r['nodes_explored']},"
                          f"{r['final_survival']:.6f}")

    (OUTPUT_DIR / "time_scan.csv").write_text("\n".join(scan_lines), encoding="utf-8")
    print(f"\nSaved: {OUTPUT_DIR / 'time_scan.csv'}")


if __name__ == "__main__":
    run_experiment()
