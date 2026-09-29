#!/usr/bin/env python3
"""Exp2 数据层：真实数据只读加载 + 降雨情景。"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from exp_common import MODULE_ROOT  # noqa: F401  （确保 src 进 sys.path）

from data_provision.pipeline import DataPipeline, PipelineResult
from data_provision.paths import get_data_paths


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


def build_rain(grid, params: dict, rain_env_cfg: dict | None = None) -> np.ndarray:
    """降雨强度场 (nx, ny, nt)，单位 mm/h —— 委托 tensor_engine.rain_environment（单一实现）。

    情景由 configs/common.yaml 的 rain_environment 节驱动（强度/时段/热点），
    params.rain 仅作实验级覆盖（enabled / scenario / intensity_mmh / active_hours /
    center / radius / spatial_mode）：

      params.rain.enabled: false   # 本实验关闭降雨（f_rain ≡ 1）

    未来接入真实降雨时，只需给 rain_environment 加 mode='real' 分支，本函数不用改。
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
    pr.rain_data = build_rain(grid, params, rain_env_cfg)
    return pr
