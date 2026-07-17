"""
Exp3 v2 纯计算版 — 无需 matplotlib
验证噪声-安全 Pareto 权衡
"""
from __future__ import annotations
import sys, json
from pathlib import Path
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

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "exp3_pareto_v2"
T_START = 22

WEIGHT_CONFIGS = [
    {"label": "w_n=0.01", "w_noise": 0.01, "w_fatality": 0.25, "w_property": 0.04, "w_distance": 0.70},
    {"label": "w_n=0.05", "w_noise": 0.05, "w_fatality": 0.25, "w_property": 0.05, "w_distance": 0.65},
    {"label": "w_n=0.10", "w_noise": 0.10, "w_fatality": 0.25, "w_property": 0.05, "w_distance": 0.60},
    {"label": "w_n=0.20", "w_noise": 0.20, "w_fatality": 0.25, "w_property": 0.05, "w_distance": 0.50},
    {"label": "w_n=0.30", "w_noise": 0.30, "w_fatality": 0.25, "w_property": 0.05, "w_distance": 0.40},
    {"label": "w_n=0.50", "w_noise": 0.50, "w_fatality": 0.20, "w_property": 0.05, "w_distance": 0.25},
    {"label": "w_n=0.70", "w_noise": 0.70, "w_fatality": 0.15, "w_property": 0.05, "w_distance": 0.10},
    {"label": "w_n=0.85", "w_noise": 0.85, "w_fatality": 0.10, "w_property": 0.03, "w_distance": 0.02},
]

def build_scenario():
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=60, ny=60, nz=12, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=24, dt_minutes=60.0),
    )
    nx, ny, nz, nt = grid.shape
    city = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=42)
    landuse = city["landuse"].astype(np.int32)
    # 住宅走廊 y=20~40
    landuse_mod = np.full_like(landuse, 6)
    landuse_mod[20:40, :] = 1
    landuse_mod[5:15, :] = 2
    landuse_mod[45:55, :] = 2

    # 确保住宅走廊有足够基础人口（合成数据可能有零值）
    pop = city["population"].astype(np.float32).copy()
    for y in range(20, 40):
        for x in range(nx):
            if pop[y, x] < 0.05:
                pop[y, x] = 0.3  # 最低基础人口
    for y in range(5, 15):
        for x in range(nx):
            if pop[y, x] < 0.05:
                pop[y, x] = 0.2
    for y in range(45, 55):
        for x in range(nx):
            if pop[y, x] < 0.05:
                pop[y, x] = 0.2

    wind = np.ones((ny, nx, nz, nt), dtype=np.float32) * 0.5
    rain = np.ones((ny, nx, nt), dtype=np.float32) * 0.0
    return {"grid": grid, "landuse": landuse_mod,
            "building_heights": city["building_heights"].astype(np.float32),
            "population": pop,
            "wind_field": wind, "rain_data": rain}

def build_env_tensor(sc, alt=50.0):
    grid = sc["grid"]
    nx, ny, nz, nt = grid.shape
    lu = sc["landuse"]
    w2d = np.transpose(sc["wind_field"][:, :, 0, :], (1, 0, 2))
    r2d = np.transpose(sc["rain_data"], (1, 0, 2))
    cm = DynamicCrashProbability()
    fw = cm.compute_wind_factor(w2d[:, :, np.newaxis, :])
    fr = cm.compute_rain_factor(r2d[:, :, np.newaxis, :])
    fo = np.ones((nx, ny, nz, nt), dtype=np.float32)
    pc = np.clip(cm.compute_pcrash(fw, fr, fo, dt=3600.0), 0, 1).astype(np.float32)
    lu_t = np.transpose(lu, (1, 0))
    bp = np.transpose(sc["population"], (1, 0))
    rp = np.zeros((nx, ny, nt), dtype=np.float32)
    for t in range(nt):
        p = bp.copy()
        h = t
        if 22 <= h or h <= 6:
            p[lu_t == 1] *= 4.0; p[lu_t == 2] *= 0.1
        else:
            p[lu_t == 1] *= 0.3; p[lu_t == 2] *= 3.0
        rp[:, :, t] = p
    rv = rp * 0.1
    fm = DynamicFatalityModel()
    ef3d = fm.compute_fatality_consequence(rho_pop=rp, rho_vehicle=rv, flight_altitude=alt)
    ef = np.broadcast_to(ef3d[:, :, np.newaxis, :], (nx, ny, nz, nt)).astype(np.float32)
    bt = np.transpose(sc["building_heights"], (1, 0))
    pm = PropertyDamageModel(building_heights=bt, max_prop_damage=1000.0, log_normal_mu=3.04, log_normal_sigma=0.5)
    ep = pm.compute_property_consequence(flight_altitude=alt).astype(np.float32)
    nm = DynamicNoiseCost(grid=grid)
    rn = nm.compute_noise_cost(landuse=lu_t, population_density=rp).astype(np.float32)
    obs = np.zeros((nx, ny, nz), dtype=np.float32)
    for iz in range(nz):
        obs[:, :, iz] = (bt >= (iz + 1.0) * grid.spatial.dz).astype(np.float32)
    return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=grid)

def main():
    print("=" * 60)
    print("Exp3 v2: Noise-Safety Pareto (Night, Residential Corridor)")
    print("=" * 60)
    sc = build_scenario()
    grid = sc["grid"]
    print(f"Grid: {grid.shape}")
    et = build_env_tensor(sc)
    print(f"Noise range: [{et.noise.min():.6f}, {et.noise.max():.6f}]")
    start = (3, 30, 5, T_START)
    goal = (56, 30, 5)
    print(f"OD: {start} -> {goal}")
    print(f"Landuse: y=20~40 residential (night penalty x10)")
    print()

    lines = ["label,w_noise,w_distance,status,path_length,final_survival,cum_fatality,cum_noise,objective_cost,runtime_ms,nodes_explored"]
    paths_data = {}
    prev_path = None
    path_changed_at = None

    for wc in WEIGHT_CONFIGS:
        cfg = {"uav_speed": 10.0, "w_distance": wc["w_distance"], "w_fatality": wc["w_fatality"],
               "w_property": wc["w_property"], "w_noise": wc["w_noise"], "survival_threshold": 0.01,
               "max_battery_time": float("inf"), "max_iterations": 2_000_000,
               "max_labels_per_cell": 8, "max_climb_rate": 5.0, "max_descent_rate": 5.0}
        planner = AStar4D(grid, et, cfg)
        result = planner.search(start, goal)
        s = result["status"]
        if s == "success":
            dl = result["total_distance"]
            sv = result["final_p_survival"]
            cf = result["cum_fatality"]
            cn = result["cum_noise"]
            J = result["objective_cost"]
            rt = result["time_cost"] * 1000
            ne = result["nodes_explored"]
            print(f"  {wc['label']:10s}  dist={dl:7.1f}m  surv={sv:.6f}  noise={cn:.6f}  fatality={cf:.8f}  J={J:.4f}  time={rt:.0f}ms  nodes={ne}")
            lines.append(f"{wc['label']},{wc['w_noise']},{wc['w_distance']},{s},{dl:.4f},{sv:.6f},{cf:.8f},{cn:.6f},{J:.6f},{rt:.1f},{ne}")
            # Track path changes
            path_key = tuple(round(step["coords"][0], 0) for step in result["path"][:10])
            if prev_path is not None and path_key != prev_path and path_changed_at is None:
                path_changed_at = wc["label"]
                print(f"    >>> PATH CHANGED at {wc['label']}!")
            prev_path = path_key
            paths_data[wc["label"]] = [step["coords"] for step in result["path"]]
        else:
            print(f"  {wc['label']:10s}  FAILED: {result.get('reason','N/A')}")
            lines.append(f"{wc['label']},{wc['w_noise']},{wc['w_distance']},{s},,,,,,,,,,")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "metrics.csv").write_text("\n".join(lines), encoding="utf-8")
    (OUTPUT_DIR / "paths.json").write_text(json.dumps(paths_data, indent=2), encoding="utf-8")
    print(f"\nSaved: {OUTPUT_DIR / 'metrics.csv'}")
    print(f"Saved: {OUTPUT_DIR / 'paths.json'}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    unique_paths = len(set(tuple(v[:10]) for v in paths_data.values()))
    print(f"  Unique paths found: {unique_paths}")
    if path_changed_at:
        print(f"  Path first changed at: {path_changed_at}")
    else:
        print(f"  WARNING: All weights produced identical path — need stronger noise contrast")

if __name__ == "__main__":
    main()
