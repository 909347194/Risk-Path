"""
Exp4 v2 纯计算版 — 无需 matplotlib
验证 Label-Setting 剪枝效率（宏观 100×100×12×96 网格）
"""
from __future__ import annotations
import sys, time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple, Optional
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

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "exp4_pruning_v2"

@dataclass
class ODPair:
    name: str
    start: Tuple[int,int,int,int]
    goal: Tuple[int,int,int]
    desc: str

def build_macro_scenario(seed=42):
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=100, ny=100, nz=12, dx=50.0, dy=50.0, dz=10.0),
        temporal=TemporalGridConfig(nt=96, dt_minutes=15.0),
    )
    nx, ny, nz, nt = grid.shape
    print(f"  Grid: {nx}×{ny}×{nz}×{nt} = {nx*ny*nz*nt:,} cells")
    city = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=seed)
    wind = city["wind_field"].astype(np.float32)
    rain = city["rain_data"].astype(np.float32)
    # 注入多个时空风热点
    yy, xx = np.mgrid[0:ny, 0:nx]
    d1 = (xx - 50)**2 + (yy - 50)**2
    d2 = (xx - 20)**2 + (yy - 80)**2
    d3 = (xx - 80)**2 + (yy - 20)**2
    h1 = np.exp(-d1/(2*12**2))
    h2 = np.exp(-d2/(2*8**2))
    h3 = np.exp(-d3/(2*8**2))
    for t in range(nt):
        hr = t * 0.25
        f1 = 6.0 if 12<=hr<=18 else (2.0 if 6<=hr<=11 else 0.5)
        f2 = 5.0 if 6<=hr<=10 else 0.5
        f3 = 5.0 if 18<=hr<=22 else 0.5
        for iz in range(nz):
            wind[:,:,iz,t] += h1*f1 + h2*f2 + h3*f3
    rh = np.exp(-d1/(2*15**2))
    for t in range(nt):
        hr = t*0.25
        if 14<=hr<=20:
            rain[:,:,t] += rh*12.0
    return {"grid":grid, "landuse":city["landuse"].astype(np.int32),
            "building_heights":city["building_heights"].astype(np.float32),
            "population":city["population"].astype(np.float32),
            "wind_field":wind, "rain_data":rain}

def build_env_tensor_macro(sc, alt=50.0):
    grid = sc["grid"]
    nx,ny,nz,nt = grid.shape
    lu = sc["landuse"]
    cm = DynamicCrashProbability()
    w2d = np.transpose(sc["wind_field"][:,:,0,:], (1,0,2))
    r2d = np.transpose(sc["rain_data"], (1,0,2))
    fw = cm.compute_wind_factor(w2d[:,:,np.newaxis,:])
    fr = cm.compute_rain_factor(r2d[:,:,np.newaxis,:])
    fo = np.ones((nx,ny,nz,nt), dtype=np.float32)
    pc = np.clip(cm.compute_pcrash(fw,fr,fo,dt=900.0),0,1).astype(np.float32)
    lu_t = np.transpose(lu, (1,0))
    bp = np.transpose(sc["population"], (1,0))
    rp = np.zeros((nx,ny,nt), dtype=np.float32)
    for t in range(nt):
        hr = t*0.25
        p = bp.copy()
        if 8<=hr<=18: p[lu_t==2]*=5.0
        else: p[lu_t==2]*=0.1
        if 22<=hr or hr<=6: p[lu_t==1]*=4.0
        elif 9<=hr<=17: p[lu_t==1]*=0.2
        if 8<=hr<=17: p[lu_t==3]*=4.0
        else: p[lu_t==3]*=0.2
        rp[:,:,t] = p
    rv = rp*0.1
    fm = DynamicFatalityModel()
    ef3d = fm.compute_fatality_consequence(rho_pop=rp, rho_vehicle=rv, flight_altitude=alt)
    ef = np.broadcast_to(ef3d[:,:,np.newaxis,:], (nx,ny,nz,nt)).astype(np.float32)
    bt = np.transpose(sc["building_heights"], (1,0))
    pm = PropertyDamageModel(building_heights=bt, max_prop_damage=1000.0, log_normal_mu=3.04, log_normal_sigma=0.5)
    ep = pm.compute_property_consequence(flight_altitude=alt).astype(np.float32)
    nm = DynamicNoiseCost(grid=grid)
    rn = nm.compute_noise_cost(landuse=lu_t, population_density=rp).astype(np.float32)
    obs = np.zeros((nx,ny,nz), dtype=np.float32)
    for iz in range(nz):
        obs[:,:,iz] = (bt>=(iz+1.0)*grid.spatial.dz).astype(np.float32)
    return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=grid)

def run_search(grid, et, od, max_labels):
    cfg = {"uav_speed":15.0, "w_distance":0.40, "w_fatality":0.30, "w_property":0.15,
           "w_noise":0.15, "survival_threshold":0.01, "max_battery_time":float("inf"),
           "max_iterations":5_000_000, "max_labels_per_cell":max_labels,
           "max_climb_rate":5.0, "max_descent_rate":5.0}
    planner = AStar4D(grid, et, cfg)
    t0 = time.time()
    result = planner.search(od.start, od.goal)
    dt = (time.time()-t0)*1000
    return {"od":od.name, "k":max_labels, "status":result["status"],
            "path_length":result.get("total_distance",float("inf")),
            "objective_cost":result.get("objective_cost",float("inf")),
            "runtime_ms":dt, "nodes_explored":result.get("nodes_explored",0)}

def main():
    print("="*60)
    print("Exp4 v2: Label-Setting Pruning (Macro 100×100×12×96)")
    print("="*60)
    print("\n[1/3] Building macro scenario...")
    sc = build_macro_scenario()
    grid = sc["grid"]
    print("\n[2/3] Building risk tensor...")
    et = build_env_tensor_macro(sc)
    print(f"  EnvTensor shape: {et.shape}")

    ods = [
        ODPair("diagonal", (5,5,5,12), (94,94,5), "SW→NE"),
        ODPair("cross_center", (5,50,5,12), (94,50,5), "W→E center"),
        ODPair("short_hop", (20,20,5,12), (80,80,5), "medium diag"),
    ]

    k_values = [1, 2, 4, 6, 8, 12, 16, 24, 32, 50, 100]
    print(f"\n[3/3] Running ablation ({len(ods)} ODs × {len(k_values)} k-values)...")

    lines_ablation = ["od,max_labels,status,path_length,objective_cost,runtime_ms,nodes_explored"]
    baseline_costs = {}  # od_name -> cost with k=100 (reference)

    # First pass: get baseline (k=100)
    for od in ods:
        r = run_search(grid, et, od, 100)
        if r["status"] == "success":
            baseline_costs[od.name] = r["objective_cost"]
        print(f"  Baseline {od.name}: k=100  cost={r['objective_cost']:.4f}  time={r['runtime_ms']:.1f}ms")

    # Full ablation
    for od in ods:
        print(f"\n  === {od.name} ({od.desc}) ===")
        for k in k_values:
            r = run_search(grid, et, od, k)
            st = f"cost={r['objective_cost']:.4f}" if r["status"]=="success" else r["status"]
            # Check optimality gap
            gap = ""
            if r["status"]=="success" and od.name in baseline_costs:
                bl = baseline_costs[od.name]
                if bl > 0:
                    pct = (r["objective_cost"]-bl)/bl*100
                    gap = f"  gap={pct:+.2f}%"
            print(f"    k={k:3d}: time={r['runtime_ms']:7.1f}ms  nodes={r['nodes_explored']:6d}  {st}{gap}")
            lines_ablation.append(f"{od.name},{k},{r['status']},{r['path_length']:.4f},"
                                  f"{r['objective_cost']:.6f},{r['runtime_ms']:.1f},{r['nodes_explored']}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR/"ablation_labels.csv").write_text("\n".join(lines_ablation), encoding="utf-8")
    print(f"\nSaved: {OUTPUT_DIR/'ablation_labels.csv'}")

    # Summary analysis
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    for od in ods:
        od_results = [r for r in [{"od":od.name,"k":k} for k in k_values]]
        # Re-read from saved data for analysis
        print(f"\n  {od.name}:")
        for k in k_values:
            r = run_search(grid, et, od, k)
            if r["status"]=="success":
                bl = baseline_costs.get(od.name, r["objective_cost"])
                gap = (r["objective_cost"]-bl)/bl*100 if bl>0 else 0
                marker = " ← OPTIMAL" if abs(gap)<0.01 else ""
                print(f"    k={k:3d}: J={r['objective_cost']:.4f} ({gap:+.2f}%)  time={r['runtime_ms']:.0f}ms  nodes={r['nodes_explored']}{marker}")

if __name__ == "__main__":
    main()
