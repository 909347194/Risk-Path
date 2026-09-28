"""
Risk Tensor Assembler — bridge from data_provision outputs to EnvTensor inputs.

Converts aligned 2D/3D NumPy matrices (from DataPipeline) into the four 4D risk
tensors that the algorithm layer consumes via EnvTensor.

Usage:
    from data_provision.pipeline import DataPipeline
    from tensor_engine.risk_tensor_assembler import build_risk_tensors
    from algorithms.env_tensor import EnvTensor

    pipeline = DataPipeline(data_type='synthetic')
    result = pipeline.run_all()
    tensors = build_risk_tensors(result, grid=pipeline.grid)
    env_tensor = EnvTensor(**tensors, grid=pipeline.grid)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np

from .grid_system import GridSystem
from .dynamic_p_crash import DynamicCrashProbability
from .dynamic_fatality import DynamicFatalityModel
from .static_obstacle import PropertyDamageModel, StaticBuildingObstacle
from .dynamic_noise import DynamicNoiseCost, get_micro_grid_noise_model
from .wind_environment import get_wind_environment, _compute_svf
from .rain_environment import get_rain_environment
from .load_config import load_config


def _cfg_get_wind_mode(cfg_node) -> str:
    """读取 wind_environment.mode，默认 'scenario'。

    接受已加载的配置（EasyDict / dict）或配置路径字符串；路径会自动 load_config。
    """
    try:
        if isinstance(cfg_node, (str, Path)):
            cfg_node = load_config(cfg_node)
        node = cfg_node
        for key in ("wind_environment", "mode"):
            if node is None:
                return "scenario"
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = getattr(node, key, None)
        return node if isinstance(node, str) else "scenario"
    except Exception:
        return "scenario"


def _as_wind_4d(wind: np.ndarray, grid: GridSystem) -> np.ndarray:
    """将风场规整为 4D (nx, ny, nz, nt)。

    - 已是 4D：直接返回（兼容 synthetic 4D 风场）。
    - 3D (nx, ny, nt)：广播到 nz（历史 legacy 行为，全高度层同风）。
    """
    if wind is None:
        raise ValueError("wind_field 为空；scenario 模式下应由 wind_environment 生成。")
    wind = np.asarray(wind, dtype=np.float32)
    nx, ny, nz, nt = grid.shape
    if wind.ndim == 4:
        if wind.shape != (nx, ny, nz, nt):
            raise ValueError(f"4D 风场形状 {wind.shape} 与网格 {grid.shape} 不符")
        return wind
    if wind.ndim == 3:
        # (nx, ny, nt) → 广播到 nz
        return np.broadcast_to(wind[:, :, np.newaxis, :], (nx, ny, nz, nt)).astype(np.float32)
    raise ValueError(f"不支持的风场维数：{wind.ndim}D")


def _compute_svf(building_heights: np.ndarray, search_radius: int = 5) -> np.ndarray:
    """从建筑高度栅格推导天空可视因子 (SVF)。

    简化模型：SVF = clip(1 - H_cell / H_max_neighbor, 0, 1)
    建筑越高、周围建筑越密集，SVF 越低（天空遮挡越严重）。
    纯 numpy 实现（无 scipy 依赖）。
    """
    h = building_heights.astype(np.float64)
    nx, ny = h.shape
    r = search_radius
    # 纯 numpy 滑动窗口最大值（zero-padding）
    h_padded = np.pad(h, r, mode="constant", constant_values=0.0)
    h_max = np.zeros_like(h)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            shifted = h_padded[r + di:r + di + nx, r + dj:r + dj + ny]
            np.maximum(h_max, shifted, out=h_max)
    h_max = np.maximum(h_max, 1.0)  # 防止除零
    svf = np.clip(1.0 - h / h_max, 0.0, 1.0)
    return svf.astype(np.float32)


def _compute_dist_to_building(
    building_heights: np.ndarray, nz: int, dz: float,
) -> np.ndarray:
    """计算到最近建筑的归一化距离场 (nx, ny, nz)。

    两遍扫描近似欧氏距离（纯 numpy，无 scipy 依赖）。
    按层高度衰减：高层的建筑影响更小。
    """
    h = building_heights
    nx, ny = h.shape
    building_mask = h > 0
    if not np.any(building_mask):
        # 无建筑 → 邶近度为 0（无峡谷放大）；返回 ones 会误报最大风险
        return np.zeros((nx, ny, nz), dtype=np.float32)

    # 两遍扫描近似 EDT（Chamfer distance，精度足够）
    INF = nx + ny + 1.0
    dist = np.where(building_mask, 0.0, INF)
    # 前向扫描
    for i in range(nx):
        for j in range(ny):
            if dist[i, j] == 0.0:
                continue
            best = dist[i, j]
            if i > 0: best = min(best, dist[i - 1, j] + 1.0)
            if j > 0: best = min(best, dist[i, j - 1] + 1.0)
            if i > 0 and j > 0: best = min(best, dist[i - 1, j - 1] + 1.414)
            if i > 0 and j < ny - 1: best = min(best, dist[i - 1, j + 1] + 1.414)
            dist[i, j] = best
    # 后向扫描
    for i in range(nx - 1, -1, -1):
        for j in range(ny - 1, -1, -1):
            if dist[i, j] == 0.0:
                continue
            best = dist[i, j]
            if i < nx - 1: best = min(best, dist[i + 1, j] + 1.0)
            if j < ny - 1: best = min(best, dist[i, j + 1] + 1.0)
            if i < nx - 1 and j < ny - 1: best = min(best, dist[i + 1, j + 1] + 1.414)
            if i < nx - 1 and j > 0: best = min(best, dist[i + 1, j - 1] + 1.414)
            dist[i, j] = best

    # 归一化到 [0, 1]，距离越近值越大（邻近度越高）
    dist_max = max(np.max(dist), 1.0)
    proximity_2d = 1.0 - dist / dist_max  # [0, 1]，越近越大

    # 逐层衰减：高度越高，建筑影响越小
    z_heights = (np.arange(nz) + 1.0) * dz
    h_ref = max(np.mean(h[h > 0]), 1.0)
    attenuation = np.exp(-z_heights / h_ref)  # (nz,)

    dist_3d = proximity_2d[:, :, np.newaxis] * attenuation[np.newaxis, np.newaxis, :]
    return dist_3d.astype(np.float32)


def compute_urban_canyon_fobs(
    building_heights: np.ndarray,
    grid: GridSystem,
    config_path: Union[str, Path, None] = None,
) -> np.ndarray:
    """计算城市峡谷风险放大系数 f_obs，返回 4D (nx, ny, nz, nt)。

    对每个 z 层用该层的实际高度计算 f_obs，体现高度越高、
    建筑影响越小的物理规律。时间维度假设静态建筑不随时间变化。

    公开入口：build_risk_tensors 与实验管线（scenario_builder / exp3~exp5）
    共用本函数，保证 f_obs 口径一致（不再各自传 np.ones 占位符）。
    """
    if config_path is None:
        project_dir = Path(__file__).resolve().parents[2]
        config_path = project_dir / "configs" / "common.yaml"
    nx, ny, nz, nt = grid.shape
    svf = _compute_svf(building_heights)
    dist_3d = _compute_dist_to_building(building_heights, nz, grid.spatial.dz)

    # 逐 z 层计算 f_obs（高度越高，峡谷效应越弱）
    f_obs_3d = np.ones((nx, ny, nz), dtype=np.float32)
    obstacle = StaticBuildingObstacle(
        svf=svf,
        building_heights=building_heights,
        dist_to_building=dist_3d,
        config_path=str(config_path),
    )
    for k in range(nz):
        z_alt = float(grid.z_heights[k])
        f_obs_3d[:, :, k] = obstacle.compute_f_obs(flight_altitude=z_alt, z_layer=k)

    # 广播到 4D：建筑是静态的，不随时间变化
    f_obs_4d = np.broadcast_to(
        f_obs_3d[:, :, :, np.newaxis], (nx, ny, nz, nt),
    ).astype(np.float32, copy=True)
    return f_obs_4d


def build_risk_tensors(
    pipeline_result,
    grid: GridSystem,
    flight_altitude: float = 50.0,
    config_path: Optional[Union[str, Path]] = None,
) -> Dict[str, np.ndarray]:
    """
    Assemble the four risk tensors from DataPipeline outputs.

    Follows the data flow: data_provision (aligned matrices) →
    tensor_engine (risk models) → four 4D risk tensors for EnvTensor.

    Args:
        pipeline_result: PipelineResult from DataPipeline.run_all(), or any
            object with attributes: landuse, building_heights, rho_population,
            rho_vehicle, wind_field, rain_data.
        grid: GridSystem instance (must match the pipeline's grid).
        flight_altitude: UAV flight altitude (m) for risk calculations.
        config_path: Path to common.yaml. If None, uses project default.

    Returns:
        Dict with keys 'p_crash', 'fatality', 'property', 'noise',
        each a numpy array ready for EnvTensor construction.
    """
    nx, ny, nz, nt = grid.shape

    if config_path is None:
        project_dir = Path(__file__).resolve().parents[2]
        config_path = project_dir / "configs" / "common.yaml"

    # Extract pipeline outputs
    landuse = pipeline_result.landuse
    building = pipeline_result.building_heights
    rho_pop = pipeline_result.rho_population
    rho_vehicle = pipeline_result.rho_vehicle
    wind = pipeline_result.wind_field
    rain = pipeline_result.rain_data

    # --- 1. Crash probability: P_crash(x,y,z,t) ---
    crash_model = DynamicCrashProbability(config_path=str(config_path))

    # 风场：情景模式由 tensor_engine 直接构建 4D 风（真正随 z、t 异质）；
    #       否则对历史 3D 风场广播到 nz（兼容 synthetic / real）。
    #       风场只作融合进 p_crash 的状态属性，不构成搜索维度。
    cfg = load_config(config_path)
    wind_mode = _cfg_get_wind_mode(cfg)
    if wind_mode == "scenario":
        # 必须传入 wind_environment *节*（dict / EasyDict），而非路径字符串：
        # get_wind_environment 只认配置节，传路径会被静默忽略并回退到硬编码默认值，
        # 导致各实验对风场的自定义配置失效（审查 HIGH 项）。
        wind_section = cfg.get("wind_environment") if isinstance(cfg, dict) else getattr(cfg, "wind_environment", None)
        wind_env = get_wind_environment(wind_section)
        svf = _compute_svf(building)
        wind_4d = wind_env.build_wind_tensor(
            grid=grid, building_heights=building, svf=svf,
        )
    else:
        wind_4d = _as_wind_4d(wind, grid)

    # 降雨：未提供实测/实验降雨场时，按配置的情景化降雨生成
    #（与风场同一原则：随 t 变化的状态属性，只进 f_rain，不构成搜索维度）
    if rain is None:
        rain_section = cfg.get("rain_environment") if isinstance(cfg, dict) \
            else getattr(cfg, "rain_environment", None)
        rain_env = get_rain_environment(rain_section)
        rain = rain_env.build_rain_tensor(grid=grid)

    rain_3d = rain[:, :, np.newaxis, :]
    f_wind = crash_model.compute_wind_factor(wind_4d)
    f_rain = crash_model.compute_rain_factor(rain_3d)
    # 城市峡谷因子：从建筑高度推导 SVF + 距离场，逐 z 层计算
    f_obs = compute_urban_canyon_fobs(building, grid, config_path)
    p_crash = crash_model.compute_pcrash(
        f_wind, f_rain, f_obs, dt=grid.temporal.dt_minutes * 60.0
    )
    p_crash = np.clip(p_crash, 0.0, 1.0).astype(np.float32)

    # --- 2. Fatality consequence: E_fatality(x,y,z,t) ---
    fatality_model = DynamicFatalityModel(config_path=config_path)
    e_fatality_2d = fatality_model.compute_fatality_consequence(
        rho_pop=rho_pop, rho_vehicle=rho_vehicle, flight_altitude=flight_altitude,
    )  # (nx, ny, nt)
    e_fatality = np.broadcast_to(
        e_fatality_2d[:, :, np.newaxis, :], (nx, ny, nz, nt)
    ).astype(np.float32)

    # --- 3. Property consequence: E_property(x,y) ---
    prop_model = PropertyDamageModel(
        building_heights=building, config_path=str(config_path),
    )
    e_property = prop_model.compute_property_consequence(
        flight_altitude=flight_altitude,
    ).astype(np.float32)

    # --- 4. Noise cost: r_noise(x,y,z,t) ---
    # 必须用调用方传入的 grid 构造噪声模型：get_micro_grid_noise_model() 会把
    # 网格锁死在 60×60 微网格，导致宏观真实数据 (100×100) 进来时
    # _as_population_4d 形状校验直接失败（审查 HIGH 项）。
    noise_model = DynamicNoiseCost(grid=grid, config_path=str(config_path))
    r_noise = noise_model.compute_noise_cost(
        landuse=landuse, population_density=rho_pop,
    ).astype(np.float32)

    return {
        "p_crash": p_crash,
        "fatality": e_fatality,
        "property": e_property,
        "noise": r_noise,
    }
