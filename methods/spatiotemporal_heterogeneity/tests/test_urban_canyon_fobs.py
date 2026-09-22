"""城市峡谷因子 f_obs 的回归测试。

背景：StaticBuildingObstacle 带 config_path 构造时，_load_config_from_yaml
曾引用尚未赋值的 self.K_obs（AttributeError），该路径长期未被测试覆盖。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

MODULE_ROOT = Path(__file__).resolve().parents[1]
if str(MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(MODULE_ROOT))

from src.tensor_engine.grid_system import (  # noqa: E402
    GridSystem, SpatialGridConfig, TemporalGridConfig,
)
from src.tensor_engine.risk_tensor_assembler import (  # noqa: E402
    compute_urban_canyon_fobs,
)
from src.tensor_engine.static_obstacle import StaticBuildingObstacle  # noqa: E402

CONFIG_PATH = MODULE_ROOT / "configs" / "common.yaml"


def _tiny_buildings(nx=8, ny=8):
    h = np.zeros((nx, ny), dtype=np.float32)
    h[3:5, 3:5] = 30.0  # 一栋 30m 建筑
    return h


def test_static_obstacle_with_config_path():
    """带 config_path 构造不再抛 AttributeError，参数从 YAML 叠加。"""
    h = _tiny_buildings()
    svf = np.ones_like(h)
    dist = np.ones((*h.shape, 3), dtype=np.float32)
    model = StaticBuildingObstacle(
        svf=svf, building_heights=h, dist_to_building=dist,
        config_path=str(CONFIG_PATH),
    )
    assert np.isfinite(model.K_obs)
    f_obs = model.compute_f_obs(flight_altitude=50.0)
    assert f_obs.shape == h.shape
    assert np.all(f_obs >= 1.0)


def test_compute_urban_canyon_fobs_shape_and_range():
    """共享 f_obs 入口返回 4D 张量，值域 [1, 1+K_obs]。"""
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=8, ny=8, nz=4, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=6, dt_minutes=60.0),
    )
    f_obs = compute_urban_canyon_fobs(_tiny_buildings(), grid, CONFIG_PATH)
    nx, ny, nz, nt = grid.shape
    assert f_obs.shape == (nx, ny, nz, nt)
    assert np.all(f_obs >= 1.0 - 1e-6)
    assert np.all(np.isfinite(f_obs))
    # 建筑应产生放大效应（非全 1 占位）
    assert float(np.max(f_obs)) > 1.0


def test_compute_urban_canyon_fobs_no_building():
    """无障碍物时退化为全 1（无放大），不崩溃。"""
    grid = GridSystem(
        spatial=SpatialGridConfig(nx=6, ny=6, nz=3, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=4, dt_minutes=60.0),
    )
    f_obs = compute_urban_canyon_fobs(
        np.zeros((6, 6), dtype=np.float32), grid, CONFIG_PATH)
    assert np.allclose(f_obs, 1.0)
