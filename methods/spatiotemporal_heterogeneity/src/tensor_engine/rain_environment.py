"""
降雨环境（情景化低空降雨强度场，可插拔）

与 wind_environment.py 对偶：降雨不是常数，而是 **空间 × 时间** 的强度场

    I(x, y, t) = I_ref(scenario) · S(x, y) · T(t)          [mm/h]

- I_ref : 情景强度（light / moderate / heavy，配置驱动，非实测）
- S(x,y): 空间分布（uniform 均匀 | hotspot 热点，热点支持硬圆盘或高斯衰减）
- T(t)  : 时间包络（active_hours 时段窗，边缘可平滑）

**只进 P_crash 的 f_rain = 1 + γ·I²，不构成搜索维度**（与风场同一原则：
状态属性随 t 变化，但不额外膨胀 4D 搜索空间）。

接入真实降雨（ERA5 等）时：新增一个 RainEnvironment 子类并在
get_rain_environment() 注册新 mode 即可，调用方无需改动。

时间/坐标约定与 grid_system 一致：返回 (nx, ny, nt)，轴序 [x, y, t]。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Optional, Union

import numpy as np


def _cfg_get(node, *keys, default=None):
    """从 dict / EasyDict 逐级取值，任一环节缺失返回 default。"""
    cur = node
    for k in keys:
        if cur is None:
            return default
        if isinstance(cur, dict):
            cur = cur.get(k, None)
        else:
            cur = getattr(cur, k, None)
    return default if cur is None else cur


class RainEnvironment(ABC):
    """降雨环境接口：给定网格产出 (nx, ny, nt) 强度场（mm/h）。"""

    @abstractmethod
    def build_rain_tensor(self, grid, time_array: Optional[np.ndarray] = None) -> np.ndarray:
        """返回 (nx, ny, nt) 降雨强度场，单位 mm/h。"""

    @abstractmethod
    def get_metadata(self) -> Dict:
        """返回可追溯的元数据（模式、情景、时段、热点等）。"""


class ScenarioRainEnvironment(RainEnvironment):
    """情景化降雨：I(x,y,t) = I_ref · S(x,y) · T(t)。"""

    def __init__(self, config: Optional[Union[dict, object]] = None,
                 scenario_name: Optional[str] = None,
                 overrides: Optional[dict] = None):
        """
        Args:
            config: rain_environment 配置节（dict / EasyDict）；None 用内置默认
            scenario_name: 情景名（light/moderate/heavy），None 用 default_scenario
            overrides: 实验级覆盖（enabled/scenario/intensity_mmh/active_hours/
                       center/radius/spatial_mode），None 表示不覆盖
        """
        ov = dict(overrides or {})
        self.enabled = bool(ov.get("enabled",
                                  _cfg_get(config, "enabled", default=True)))

        # ---- 情景强度 I_ref ----
        name = ov.get("scenario") or scenario_name \
            or _cfg_get(config, "default_scenario", default="moderate")
        scenarios = _cfg_get(config, "scenarios", default=None) or {
            "light": {"intensity_mmh": 2.0},
            "moderate": {"intensity_mmh": 8.0},
            "heavy": {"intensity_mmh": 25.0},
        }
        sc = scenarios.get(name) if isinstance(scenarios, dict) else None
        if sc is None:
            raise ValueError(f"未知降雨情景：'{name}'（可选 {sorted(scenarios)}）")
        self.scenario_name = name
        self.intensity_mmh = float(ov.get("intensity_mmh")
                                   or _cfg_get(sc, "intensity_mmh", default=8.0))

        # ---- 时间包络 T(t) ----
        tv = _cfg_get(config, "temporal", default=None) or {}
        self.temporal_enabled = bool(_cfg_get(tv, "enabled", default=True))
        self.active_hours = list(ov.get("active_hours")
                                 or _cfg_get(tv, "active_hours", default=[14, 20]))
        self.edge_softness = float(_cfg_get(tv, "edge_softness", default=0.5))

        # ---- 空间分布 S(x,y) ----
        sp = _cfg_get(config, "spatial", default=None) or {}
        self.spatial_mode = str(ov.get("spatial_mode")
                                or _cfg_get(sp, "mode", default="hotspot"))
        self.center = ov.get("center", _cfg_get(sp, "center", default=None))
        self.radius = float(ov.get("radius", _cfg_get(sp, "radius", default=20.0)))
        self.falloff = str(_cfg_get(sp, "falloff", default="smooth"))

    # ------------------------------------------------------------------
    def _spatial_factor(self, nx: int, ny: int) -> np.ndarray:
        """S(x, y) ∈ [0, 1]。"""
        if self.spatial_mode == "uniform":
            return np.ones((nx, ny), dtype=np.float32)

        cx, cy = self.center if self.center else (nx / 2.0, ny / 2.0)
        yy, xx = np.mgrid[0:ny, 0:nx]
        # 注意 mgrid 的行是 y、列是 x；转成 [x, y] 轴序
        dist = np.sqrt((xx.T - cx) ** 2 + (yy.T - cy) ** 2)

        if self.falloff == "hard":
            return (dist <= self.radius).astype(np.float32)
        # smooth：高斯衰减，半径处约 0.6 倍
        sigma = max(self.radius, 1e-6) / 2.0
        return np.exp(-(dist ** 2) / (2.0 * sigma ** 2)).astype(np.float32)

    def _temporal_factor(self, time_hours: np.ndarray) -> np.ndarray:
        """T(t) ∈ [0, 1]。矩形窗 + 可选边缘平滑（softness=0 退化为硬窗）。"""
        if not self.temporal_enabled:
            return np.ones(time_hours.shape, dtype=np.float32)

        h0, h1 = float(self.active_hours[0]), float(self.active_hours[1])
        if h1 < h0:                      # 跨午夜（如 22→6）
            h1 += 24.0
        tt = np.where(time_hours < h0, time_hours + 24.0, time_hours)

        s = max(self.edge_softness, 1e-6)
        rise = 1.0 / (1.0 + np.exp(-(tt - h0) / s))
        fall = 1.0 / (1.0 + np.exp((tt - h1) / s))
        return (rise * fall).astype(np.float32)

    def _resolve_time(self, grid, time_array: Optional[np.ndarray]) -> np.ndarray:
        if time_array is not None:
            return np.asarray(time_array, dtype=np.float64)
        nt = grid.shape[3]
        dt_minutes = getattr(grid.temporal, "dt_minutes", 15.0)
        return np.arange(nt) * (dt_minutes / 60.0)

    # ------------------------------------------------------------------
    def build_rain_tensor(self, grid, time_array: Optional[np.ndarray] = None) -> np.ndarray:
        nx, ny, _, nt = grid.shape
        if not self.enabled:
            return np.zeros((nx, ny, nt), dtype=np.float32)
        time_hours = self._resolve_time(grid, time_array)
        s = self._spatial_factor(nx, ny)[:, :, None]          # (nx, ny, 1)
        t = self._temporal_factor(time_hours)[None, None, :]   # (1, 1, nt)
        return (self.intensity_mmh * s * t).astype(np.float32)

    def get_metadata(self) -> Dict:
        return {
            "mode": "scenario",
            "enabled": self.enabled,
            "scenario": self.scenario_name,
            "intensity_mmh": self.intensity_mmh,
            "active_hours": list(self.active_hours),
            "edge_softness": self.edge_softness,
            "spatial_mode": self.spatial_mode,
            "center": list(self.center) if self.center else "region-center",
            "radius_grids": self.radius,
            "falloff": self.falloff,
        }

    def save(self, tensors_dir: Union[str, "Path"], data_type: str = "synthetic") -> Dict:  # noqa: F821
        """与 wind_environment 一致的可追溯落盘（元数据 JSON）。"""
        import json
        from pathlib import Path
        out = Path(tensors_dir) / f"rain_environment_{data_type}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        meta = self.get_metadata()
        out.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"rain_meta": str(out)}


def get_rain_environment(
    config: Optional[Union[dict, object]] = None,
    scenario_name: Optional[str] = None,
    overrides: Optional[dict] = None,
) -> RainEnvironment:
    """根据配置返回降雨环境实例。

    当前仅支持 scenario 模式；接入真实降雨（ERA5）时在此分支注册新 mode。
    """
    mode = _cfg_get(config, "mode", default="scenario")
    if mode == "scenario":
        return ScenarioRainEnvironment(config=config, scenario_name=scenario_name,
                                       overrides=overrides)
    raise ValueError(
        f"不支持的降雨环境模式：'{mode}'（当前仅支持 'scenario'；"
        f"真实降雨数据接入后可注册 'real' 分支）"
    )
