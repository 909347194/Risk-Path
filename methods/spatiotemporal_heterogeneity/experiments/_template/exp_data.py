#!/usr/bin/env python3
"""实验数据层（通用件）：真实数据只读加载 + 合成管线切换。

注意：DataPipeline(data_type='real').run_all() 会从 01_raw 重算并**覆盖**
data/02_processed 的已提交数据。多数实验应使用 load_prepared_real_data()
只读加载「准备好的」数组，而不是 run_all()。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401  （确保 src 进 sys.path）

from data_provision.pipeline import DataPipeline, PipelineResult
from data_provision.paths import get_data_paths


def load_prepared_real_data(grid) -> PipelineResult:
    """只读加载 data/02_processed 已准备的真实数据（含形状校验）。"""
    paths = get_data_paths("real")
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

    poi_npz = _load(paths.poi_counts_path, "poi_counts")
    poi_counts = {k: poi_npz[k] for k in poi_npz.files if k != "categories"}

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
            raise ValueError(f"真实数据 {name} 形状 {arr.shape} 与网格 {expect} 不符")
    for k, v in poi_counts.items():
        if tuple(v.shape) != (nx, ny):
            raise ValueError(f"POI {k} 形状 {v.shape} 与网格 {(nx, ny)} 不符")

    print(f"[Data] 只读加载已准备真实数据: {paths.processed}")
    return PipelineResult(
        landuse=landuse, building_heights=building, road_mask=road,
        base_population=base_pop, poi_counts=poi_counts,
        rho_population=rho_pop, rho_vehicle=rho_vehicle,
        wind_field=None, rain_data=None, paths=paths,
    )


def build_rain(grid, params: dict, rain_env_cfg: dict | None = None) -> np.ndarray:
    """降雨强度场 (nx, ny, nt)，单位 mm/h —— 委托 tensor_engine.rain_environment（单一实现）。

    情景由 configs/common.yaml 的 rain_environment 节驱动（强度/时段/热点），
    params.rain 仅作实验级覆盖（enabled / scenario / intensity_mmh / active_hours /
    center / radius / spatial_mode）。默认启用情景降雨（中雨 8mm/h，14–20 时热点）；
    要关闭就在本实验 config.yaml 写 `params.rain.enabled: false`。
    """
    from tensor_engine.rain_environment import get_rain_environment

    overrides = dict(params.get("rain") or {})
    env = get_rain_environment(rain_env_cfg, overrides=overrides or None)
    return env.build_rain_tensor(grid)


def load_experiment_data(grid, data_type: str, params: dict,
                         rain_env_cfg: dict | None = None) -> PipelineResult:
    """按 data.type 装配实验数据（real 只读加载 / synthetic 走 DataPipeline）。"""
    if data_type == "real":
        pr = load_prepared_real_data(grid)
    else:
        pr = DataPipeline(data_type=data_type).run_all(skip_weather=True)
    # 实验专属数据加工追加在此；降雨统一走 build_rain（情景模型）
    pr.rain_data = build_rain(grid, params, rain_env_cfg)
    return pr
