"""
W4: 随机 OD 采样统计 — 证明 Pareto 前沿不是精心挑选出来的

设计：
- 在 60×60 网格上随机采样 N 个 OD 对
- 每个 OD 对运行 2 组权重：低 w_noise (0.05) 和高 w_noise (0.50)
- 统计有多少比例的 OD 对产生了不同路径
- 这证明 Pareto 效应是普遍存在的，不是特定 OD 的偶然结果
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

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "micro_comprehensive"


def build_scenario(seed=42):
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=60, ny=60, nz=12, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=24, dt_minutes=60.0),
    )
    nx, ny, nz, nt = grid.shape
    city = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=seed)
    landuse = city["landuse"].astype(np.int32)
    bh = city["building_heights"].astype(np.float32)
    wind = city["wind_field"].astype(np.float32)
    rain = city["rain_data"].astype(np.float32)

    # 风场热点
    cy, cx = ny // 2, nx // 2
    yy, xx = np.mgrid[0:ny, 0:nx]
    dsq = (xx - cx)**2 + (yy - cy)**2
    hs = np.exp(-dsq / (2 * 8**2))
    for t in range(nt):
        f = 8.0 if 12 <= t <= 18 else (4.0 if 6 <= t <= 11 else 1.0)
        for iz in range(nz):
            wind[:, :, iz, t] += hs * f

    # 降雨热点
    rhs = np.exp(-dsq / (2 * 10**2))
    for t in range(nt):
        if 14 <= t <= 20:
            rain[:, :, t] += rhs * 15.0

    # 人口潮汐
    lu_t = np.transpose(landuse, (1, 0))
    bp = np.transpose(city["population"].astype(np.float32), (1, 0))
    rp = np.zeros((nx, ny, nt), dtype=np.float32)
    for t in range(nt):
        p = bp.copy()
        if 8 <= t <= 18: p[lu_t == 2] *= 5.0
        else: p[lu_t == 2] *= 0.1
        if 22 <= t or t <= 6: p[lu_t == 1] *= 4.0
        elif 9 <= t <= 17: p[lu_t == 1] *= 0.2
        if 8 <= t <= 17: p[lu_t == 3] *= 4.0
        else: p[lu_t == 3] *= 0.2
        rp[:, :, t] = p

    return grid, landuse, bh, wind, rain, rp


def build_env_tensor(grid, landuse, bh, wind, rain, rp, alt=50.0):
    nx, ny, nz, nt = grid.shape
    cm = DynamicCrashProbability()
    w2d = np.transpose(wind[:, :, 0, :], (1, 0, 2))
    r2d = np.transpose(rain, (1, 0, 2))
    fw = cm.compute_wind_factor(w2d[:, :, np.newaxis, :])
    fr = cm.compute_rain_factor(r2d[:, :, np.newaxis, :])
    fo = np.ones((nx, ny, nz, nt), dtype=np.float32)
    pc = np.clip(cm.compute_pcrash(fw, fr, fo, dt=3600.0), 0, 1).astype(np.float32)

    rv = rp * 0.1
    fm = DynamicFatalityModel()
    ef3d = fm.compute_fatality_consequence(rho_pop=rp, rho_vehicle=rv, flight_altitude=alt)
    ef = np.broadcast_to(ef3d[:, :, np.newaxis, :], (nx, ny, nz, nt)).astype(np.float32)

    bt = np.transpose(bh, (1, 0))
    pm = PropertyDamageModel(building_heights=bt, max_prop_damage=1000.0, log_normal_mu=3.04, log_normal_sigma=0.5)
    ep = pm.compute_property_consequence(flight_altitude=alt).astype(np.float32)

    nm = DynamicNoiseCost(grid=grid)
    lu_t = np.transpose(landuse, (1, 0))
    rn = nm.compute_noise_cost(landuse=lu_t, population_density=rp).astype(np.float32)

    obs = np.zeros((nx, ny, nz), dtype=np.float32)
    for iz in range(nz):
        obs[:, :, iz] = (bt >= (iz + 1.0) * grid.spatial.dz).astype(np.float32)

    return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=grid)


def run_search(grid, et, start, goal, w_noise, w_distance):
    config = {
        "uav_speed": 10.0, "w_distance": w_distance, "w_fatality": 0.30,
        "w_property": 0.10, "w_noise": w_noise, "survival_threshold": 0.01,
        "max_battery_time": float("inf"), "max_iterations": 2_000_000,
        "max_labels_per_cell": 8, "max_climb_rate": 5.0, "max_descent_rate": 5.0,
    }
    planner = AStar4D(grid, et, config)
    result = planner.search(start, goal)
    if result["status"] == "success":
        path = [step["coords"][:3] for step in result["path"]]
        return {
            "status": "success",
            "path": path,
            "path_length": result["total_distance"],
            "objective_cost": result["objective_cost"],
            "cum_noise": result["cum_noise"],
            "final_survival": result["final_p_survival"],
            "cum_fatality": result["cum_fatality"],
        }
    return {"status": "failed"}


def path_signature(path):
    """路径签名：取前 10 个和后 10 个坐标点作为指纹。"""
    if len(path) <= 20:
        return tuple(path)
    return tuple(path[:10]) + tuple(path[-10:])


def main():
    print("=" * 60)
    print("W4: Random OD Sampling — Pareto Robustness")
    print("=" * 60)

    N_OD = 100  # 采样 100 个随机 OD 对
    MIN_DIST = 15  # 最短距离（格）
    Z_LEVEL = 5
    T_START = 22  # 夜间出发（噪声惩罚最大）

    print(f"\n[1/3] Building scenario...")
    grid, landuse, bh, wind, rain, rp = build_scenario()
    et = build_env_tensor(grid, landuse, bh, wind, rain, rp)
    nx, ny = grid.spatial.nx, grid.spatial.ny
    print(f"  Grid: {grid.shape}, OD samples: {N_OD}, depart: t={T_START} (night)")

    print(f"\n[2/3] Sampling {N_OD} random OD pairs and testing...")

    # 两组权重
    W_LOW = {"w_noise": 0.05, "w_distance": 0.50}
    W_HIGH = {"w_noise": 0.50, "w_distance": 0.10}

    rng = np.random.default_rng(123)
    results = []
    path_changed_count = 0
    both_success_count = 0

    for i in range(N_OD):
        # 随机采样 OD（确保距离足够远）
        for _ in range(100):  # 最多尝试 100 次
            sx, sy = rng.integers(5, nx - 5), rng.integers(5, ny - 5)
            gx, gy = rng.integers(5, nx - 5), rng.integers(5, ny - 5)
            dist = np.sqrt((gx - sx)**2 + (gy - sy)**2)
            if dist >= MIN_DIST:
                break

        start = (sx, sy, Z_LEVEL, T_START)
        goal = (gx, gy, Z_LEVEL)

        # 低 w_noise
        r_low = run_search(grid, et, start, goal, W_LOW["w_noise"], W_LOW["w_distance"])
        # 高 w_noise
        r_high = run_search(grid, et, start, goal, W_HIGH["w_noise"], W_HIGH["w_distance"])

        if r_low["status"] == "success" and r_high["status"] == "success":
            both_success_count += 1
            sig_low = path_signature(r_low["path"])
            sig_high = path_signature(r_high["path"])
            paths_differ = (sig_low != sig_high)

            if paths_differ:
                path_changed_count += 1

            results.append({
                "od_idx": i,
                "start": (sx, sy),
                "goal": (gx, gy),
                "dist_euclidean": dist,
                "path_changed": paths_differ,
                "low_noise": r_low["cum_noise"],
                "high_noise": r_high["cum_noise"],
                "low_length": r_low["path_length"],
                "high_length": r_high["path_length"],
                "low_survival": r_low["final_survival"],
                "high_survival": r_high["final_survival"],
                "low_fatality": r_low["cum_fatality"],
                "high_fatality": r_high["cum_fatality"],
            })

            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{N_OD}] tested, {path_changed_count} paths changed so far")

    # ===== 统计 =====
    print(f"\n[3/3] Statistics:")
    print(f"  Total OD pairs tested: {N_OD}")
    print(f"  Both algorithms succeeded: {both_success_count}")
    print(f"  Paths changed (low vs high w_noise): {path_changed_count}")
    if both_success_count > 0:
        pct = path_changed_count / both_success_count * 100
        print(f"  Pareto-relevant OD ratio: {pct:.1f}%")

    # 分析路径变化时的噪声差异
    changed = [r for r in results if r["path_changed"]]
    unchanged = [r for r in results if not r["path_changed"]]

    if changed:
        avg_noise_low_c = np.mean([r["low_noise"] for r in changed])
        avg_noise_high_c = np.mean([r["high_noise"] for r in changed])
        avg_len_low_c = np.mean([r["low_length"] for r in changed])
        avg_len_high_c = np.mean([r["high_length"] for r in changed])
        print(f"\n  Changed paths ({len(changed)} ODs):")
        print(f"    avg noise:  low_w={avg_noise_low_c:.6f}  high_w={avg_noise_high_c:.6f}  delta={avg_noise_low_c-avg_noise_high_c:.6f}")
        print(f"    avg length: low_w={avg_len_low_c:.1f}m  high_w={avg_len_high_c:.1f}m  delta={avg_len_high_c-avg_len_low_c:.1f}m")

    if unchanged:
        avg_noise_low_u = np.mean([r["low_noise"] for r in unchanged])
        avg_noise_high_u = np.mean([r["high_noise"] for r in unchanged])
        print(f"\n  Unchanged paths ({len(unchanged)} ODs):")
        print(f"    avg noise:  low_w={avg_noise_low_u:.6f}  high_w={avg_noise_high_u:.6f}  delta={avg_noise_low_u-avg_noise_high_u:.6f}")

    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["od_idx,start_x,start_y,goal_x,goal_y,dist_euclidean,path_changed,"
              "low_noise,high_noise,low_length,high_length,low_survival,high_survival,"
              "low_fatality,high_fatality"]
    for r in results:
        lines.append(f"{r['od_idx']},{r['start'][0]},{r['start'][1]},{r['goal'][0]},{r['goal'][1]},"
                     f"{r['dist_euclidean']:.1f},{r['path_changed']},"
                     f"{r['low_noise']:.6f},{r['high_noise']:.6f},"
                     f"{r['low_length']:.4f},{r['high_length']:.4f},"
                     f"{r['low_survival']:.6f},{r['high_survival']:.6f},"
                     f"{r['low_fatality']:.8f},{r['high_fatality']:.8f}")
    csv_path = OUTPUT_DIR / "random_od_pareto.csv"
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n  Saved: {csv_path}")

    # 总结
    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)
    if both_success_count > 0:
        pct = path_changed_count / both_success_count * 100
        print(f"  {pct:.1f}% of random OD pairs show different paths")
        print(f"  when w_noise changes from 0.05 to 0.50.")
        if pct > 10:
            print(f"  → Pareto effect is ROBUST, not cherry-picked.")
        elif pct > 0:
            print(f"  → Pareto effect exists but is scenario-dependent.")
        else:
            print(f"  → Pareto effect not observed in random sampling.")


if __name__ == "__main__":
    main()
