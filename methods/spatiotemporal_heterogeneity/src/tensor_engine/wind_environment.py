"""
Scenario-based low-altitude UAV wind environment model.

================================================================================
定位（重要）
================================================================================
本模块 **不是 CFD**，也 **不重建真实城市微尺度风场**。研究区缺乏支撑微尺度
风场重建的高分辨率实测数据，因此本模块借鉴 Dong et al. (2026) 对风环境
“空间 / 高度 / 时间异质性” 的建模思想，构建 **情景化低空风环境**，用于
UAV 动态风险评价（P_crash）与 TD-RiskA* 路径规划。

核心公式：

    V(x, y, z, t) = V_ref(t) · F_z(z) · F_urban(x, y) · F_gust(t)

- V_ref(t) : 背景典型风速情景（配置驱动，非实测）
- F_z(z)    : 高度修正（risk-oriented vertical modifier，非 ABL 物理廓线）
- F_urban   : 城市形态空间修正（**遮蔽衰减**，见下方“双计权约束”）
- F_gust(t) : 可选阵风扰动（默认关闭，保证确定性实验）

================================================================================
两条硬约束（由项目要求强制）
================================================================================
(1) F_urban 与已有城市峡谷风险 **绝不重复计权**。
    现有 dynamic_p_crash.compute_urban_factor() 产出 R_canyon，作为 f_obs
    进入危险率 Φ = f_wind · f_rain · f_obs（放大效应，f_obs ≥ 1）。
    本模块的 F_urban 采用 **独立的遮蔽衰减** 形式：
        C_shelter = clip(1 - SVF, 0, 1)            # 开敞≈0，深峡谷≈1
        F_urban   = clip(1 - β · C_shelter, F_min, F_max)
    即：城市密集区风速“被遮蔽而衰减”（F_urban ≤ 1，削弱 f_wind），而 f_obs
    是“障碍物放大坠机概率”（≥ 1）。二者输入（SVF 等）相关，但 **机制独立、
    符号相反**：F_urban 绝不写成 `1 + α · R_canyon`，绝不调用
    compute_urban_factor / StaticBuildingObstacle。因此建筑效应不会被乘两遍。

(2) 风场永远只作为 **在线查询的状态属性**，绝不膨胀成显式 4D 搜索空间。
    本模块产出 V(x,y,z,t) 这一 4D 张量，但它被 risk_tensor_assembler 融合进
    p_crash 风险张量；TD-RiskA* 仅按路径传播出的累计时间 t_j 在线索引该张量
    （risk_at），时间 t 是路径状态属性，**不构成搜索维度**。sample_speed()
    仅作为可插拔的在线查询接口，供未来（如侧风/逆风）扩展使用，不改变上述
    架构。

================================================================================
可插拔设计
================================================================================
WindEnvironment 为抽象基类；当前唯一实现为 ScenarioWindEnvironment。
未来若接入 Dong 式 16 分区 / 真实 ERA5 / u-v 风矢量，只需新增子类并在
get_wind_environment() 注册，无需改动调用方。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np

from .grid_system import GridSystem

WIND_ENVIRONMENT_KIND = "scenario_based_low_altitude_wind_environment"


# ----------------------------------------------------------------------------
# 配置读取辅助：兼容 EasyDict（属性访问）与纯 dict
# ----------------------------------------------------------------------------
def _cfg_get(node, *keys, default=None):
    """按点分路径读取配置，兼容 EasyDict / dict，缺失返回 default。"""
    for key in keys:
        if node is None:
            return default
        val = None
        if isinstance(node, dict):
            if key in node:
                val = node[key]
            else:
                return default
        else:
            try:
                val = getattr(node, key)
            except AttributeError:
                try:
                    val = node[key]
                except (KeyError, TypeError, IndexError):
                    return default
        node = val
    return node if node is not None else default


# ----------------------------------------------------------------------------
# 局部 SVF 计算（与 risk_tensor_assembler._compute_svf 口径一致）
# 说明：此处仅用于风“遮蔽”指标，刻意 **不复用** compute_urban_factor / R_canyon，
#       以满足约束 (1)。若调用方已提供 svf，则优先使用传入值。
# ----------------------------------------------------------------------------
def _compute_svf(building_heights: np.ndarray, search_radius: int = 5) -> np.ndarray:
    """从建筑高度栅格推导天空可视因子 SVF ∈ [0, 1]。

    纯 numpy 实现（无 scipy 依赖）。SVF 越高代表越开敞，越低代表峡谷越深。
    """
    h = building_heights.astype(np.float64)
    nx, ny = h.shape
    r = search_radius
    h_padded = np.pad(h, r, mode="constant", constant_values=0.0)
    h_max = np.zeros_like(h)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            shifted = h_padded[r + di: r + di + nx, r + dj: r + dj + ny]
            np.maximum(h_max, shifted, out=h_max)
    h_max = np.maximum(h_max, 1.0)
    svf = np.clip(1.0 - h / h_max, 0.0, 1.0)
    return svf.astype(np.float32)


# ----------------------------------------------------------------------------
# 抽象基类
# ----------------------------------------------------------------------------
class WindEnvironment(ABC):
    """风环境模型抽象接口（可插拔）。

    子类负责把“情景 / 数据”转化为 4D 风速张量 V(x,y,z,t)，并提供在线查询。
    """

    kind: str = "base"

    @abstractmethod
    def build_wind_tensor(
        self,
        grid: GridSystem,
        building_heights: np.ndarray,
        svf: Optional[np.ndarray] = None,
        dist_to_building: Optional[np.ndarray] = None,
        time_array: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """构建 4D 风速张量 (nx, ny, nz, nt)，float32，单位 m/s。"""
        raise NotImplementedError

    @abstractmethod
    def get_metadata(self) -> Dict:
        """返回模型元数据（含 is_observed: False 防误用）。"""
        raise NotImplementedError

    def sample_speed(
        self,
        ix: float, iy: float, iz: float, t_seconds: float,
    ) -> float:
        """在线查询风速（可插拔接口）。

        子类已实现 build_wind_tensor 后可基于张量做插值查询；默认抛 NotImplemented。
        参数单位：ix,iy,iz 为网格浮点索引；t_seconds 为绝对飞行时间（秒）。
        """
        raise NotImplementedError


# ----------------------------------------------------------------------------
# 情景化低空风环境实现
# ----------------------------------------------------------------------------
class ScenarioWindEnvironment(WindEnvironment):
    """Scenario-based low-altitude UAV wind environment model.

    乘性分解：V = V_ref(t) · F_z(z) · F_urban(x,y) · F_gust(t)
    """

    kind = WIND_ENVIRONMENT_KIND

    def __init__(
        self,
        config: Optional[Union[dict, object]] = None,
        scenario_name: Optional[str] = None,
    ):
        """
        Args:
            config: wind_environment 配置节（EasyDict 或 dict）。可为 None，
                    此时全部使用规格默认值。
            scenario_name: 覆盖默认情景（'weak' / 'moderate' / 'strong'）。
        """
        self.cfg = config
        self._grid: Optional[GridSystem] = None
        self._wind_4d: Optional[np.ndarray] = None
        self._time_hours: Optional[np.ndarray] = None

        # --- mode / scenario ---
        self.mode = _cfg_get(config, "mode", default="scenario")
        self.default_scenario = _cfg_get(config, "default_scenario", default="moderate")
        self.scenario_name = scenario_name or self.default_scenario

        # --- scenarios: reference speed (m/s) ---
        scenarios = _cfg_get(config, "scenarios", default={}) or {}
        self.scenarios = {
            name: float(_cfg_get(sc, "reference_speed", default=6.0))
            for name, sc in scenarios.items()
        } if scenarios else {"weak": 3.0, "moderate": 6.0, "strong": 9.0}
        if self.scenario_name not in self.scenarios:
            raise KeyError(
                f"未知风情景 '{self.scenario_name}'；可用：{list(self.scenarios)}"
            )
        self.reference_speed = self.scenarios[self.scenario_name]

        # --- temporal variation ---
        tv = _cfg_get(config, "temporal_variation", default={}) or {}
        self.temporal_enabled = bool(_cfg_get(tv, "enabled", default=True))
        self.temporal_amplitude = float(_cfg_get(tv, "amplitude", default=0.15))
        self.temporal_period_hours = float(_cfg_get(tv, "period_hours", default=24.0))
        self.temporal_phase = float(_cfg_get(tv, "phase", default=0.0))

        # --- vertical profile (F_z) ---
        vp = _cfg_get(config, "vertical_profile", default={}) or {}
        self.vertical_enabled = bool(_cfg_get(vp, "enabled", default=True))
        self.vertical_min = float(_cfg_get(vp, "min_factor", default=0.85))
        self.vertical_max = float(_cfg_get(vp, "max_factor", default=1.20))

        # --- urban modifier (F_urban，遮蔽衰减) ---
        um = _cfg_get(config, "urban_modifier", default={}) or {}
        self.urban_enabled = bool(_cfg_get(um, "enabled", default=True))
        self.urban_beta = float(_cfg_get(um, "beta", default=0.20))
        self.urban_min = float(_cfg_get(um, "min_factor", default=0.80))
        self.urban_max = float(_cfg_get(um, "max_factor", default=1.05))

        # --- gust (AR(1)，默认关闭) ---
        g = _cfg_get(config, "gust", default={}) or {}
        self.gust_enabled = bool(_cfg_get(g, "enabled", default=False))
        self.gust_rho = float(_cfg_get(g, "rho", default=0.85))
        self.gust_sigma = float(_cfg_get(g, "sigma", default=0.10))
        self.gust_min = float(_cfg_get(g, "min_factor", default=0.80))
        self.gust_max = float(_cfg_get(g, "max_factor", default=1.25))
        self.gust_seed = int(_cfg_get(g, "seed", default=42))

    # ------------------------------------------------------------------ #
    # 各因子计算
    # ------------------------------------------------------------------ #
    def _resolve_time(self, grid: GridSystem, time_array: Optional[np.ndarray]) -> np.ndarray:
        """解析时间轴（单位：小时）。time_array 若为秒需调用方自行转换。"""
        if time_array is not None:
            # 允许传入秒或小时；以 > 1e4 阈值粗判“疑似秒”并转换
            arr = np.asarray(time_array, dtype=np.float64)
            if arr.size and float(arr.max()) > 1e4:
                arr = arr / 3600.0
            return arr
        nt = grid.temporal.nt
        dt_min = float(grid.temporal.dt_minutes)
        # 取每个时间片中点，单位小时
        return (np.arange(nt) + 0.5) * dt_min / 60.0

    def _temporal_factor(self, time_hours: np.ndarray) -> np.ndarray:
        """V_ref(t) = V0 · [1 + A_t · sin(2π t / T + φ)]，返回 (nt,)。"""
        if not self.temporal_enabled:
            return np.ones(time_hours.shape, dtype=np.float32)
        arg = 2.0 * np.pi * time_hours / self.temporal_period_hours + self.temporal_phase
        factor = 1.0 + self.temporal_amplitude * np.sin(arg)
        return factor.astype(np.float32)

    def _vertical_factor(self, z_heights: np.ndarray) -> np.ndarray:
        """F_z(z)：在 [z_min, z_max] 之间由 vertical_min 平滑插值到 vertical_max。

        注：规格 §6 文字写 “1 + A_z·norm”，但给定端点 F_z(z_min)=0.85、
        F_z(z_max)=1.20 与该式不符（后者在 z_min 处恒为 1）。此处按 **端点优先**
        实现为归一化线性插值 min + (max-min)·norm，与测试 V(z_max)>V(z_min)
        及 “risk-oriented vertical modifier” 的语义一致。
        """
        z = np.asarray(z_heights, dtype=np.float64)
        if not self.vertical_enabled:
            return np.ones(z.shape, dtype=np.float32)
        z_min, z_max = float(z.min()), float(z.max())
        if z_max - z_min < 1e-9:
            norm = np.zeros_like(z)
        else:
            norm = (z - z_min) / (z_max - z_min)
        norm = np.clip(norm, 0.0, 1.0)
        fz = self.vertical_min + (self.vertical_max - self.vertical_min) * norm
        return fz.astype(np.float32)

    def _urban_shelter(
        self,
        building_heights: np.ndarray,
        svf: Optional[np.ndarray],
    ) -> np.ndarray:
        """F_urban(x,y)：城市形态 **遮蔽衰减**（满足双计权约束 (1)）。

        C_shelter = clip(1 - SVF, 0, 1)          # 开敞≈0，深峡谷≈1
        F_urban   = clip(1 - β·C_shelter, F_min, F_max)

        这是与 f_obs(R_canyon) **独立** 的机制：F_urban 衰减风速（≤1），
        f_obs 放大危险（≥1）。二者绝不共用同一公式或符号。
        """
        h = np.asarray(building_heights, dtype=np.float64)
        if svf is None:
            svf_arr = _compute_svf(h)
        else:
            svf_arr = np.asarray(svf, dtype=np.float64)
        svf_arr = np.clip(svf_arr, 0.0, 1.0)
        if not self.urban_enabled:
            return np.ones(svf_arr.shape, dtype=np.float32)
        c_shelter = np.clip(1.0 - svf_arr, 0.0, 1.0)
        f_urban = 1.0 - self.urban_beta * c_shelter
        f_urban = np.clip(f_urban, self.urban_min, self.urban_max)
        return f_urban.astype(np.float32)

    def _gust_factor(self, nt: int) -> Union[float, np.ndarray]:
        """F_gust(t)：默认关闭 → 1；开启 → AR(1) 序列，接受 seed 保证可复现。"""
        if not self.gust_enabled:
            return 1.0
        rng = np.random.default_rng(self.gust_seed)
        xi = rng.standard_normal(nt)  # 局部 RNG，不污染全局状态
        g = np.zeros(nt, dtype=np.float64)
        scale = np.sqrt(1.0 - self.gust_rho ** 2) * self.gust_sigma
        for t in range(nt):
            if t == 0:
                g[t] = scale * xi[t]
            else:
                g[t] = self.gust_rho * g[t - 1] + scale * xi[t]
        f_gust = np.clip(1.0 + g, self.gust_min, self.gust_max)
        return f_gust.astype(np.float32)

    # ------------------------------------------------------------------ #
    # 主入口
    # ------------------------------------------------------------------ #
    def build_wind_tensor(
        self,
        grid: GridSystem,
        building_heights: np.ndarray,
        svf: Optional[np.ndarray] = None,
        dist_to_building: Optional[np.ndarray] = None,
        time_array: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """构建 4D 风速张量 (nx, ny, nz, nt)，float32，单位 m/s。

        高度维 (nz) 仅在此处（tensor_engine）扩展；data_provision 不创建 nz。
        dist_to_building 当前保留为扩展接口（未来 u-v 风矢量可复用），
        本情景模型仅用 building_heights + svf 计算遮蔽。
        """
        self._grid = grid
        nx, ny, nz, nt = grid.shape
        z_heights = grid.z_heights.astype(np.float64)

        time_hours = self._resolve_time(grid, time_array)
        self._time_hours = time_hours

        v_ref = self._temporal_factor(time_hours)              # (nt,)
        f_z = self._vertical_factor(z_heights)                  # (nz,)
        f_urban = self._urban_shelter(building_heights, svf)    # (nx, ny)
        f_gust = self._gust_factor(nt)                         # scalar 或 (nt,)

        # 广播：(nx,ny,1,1) · (1,1,1,nt) · (1,1,nz,1) · (1,1,1,nt 或标量)
        v_ref_b = v_ref.reshape(1, 1, 1, nt)
        f_z_b = f_z.reshape(1, 1, nz, 1)
        f_urban_b = f_urban.reshape(nx, ny, 1, 1)
        if np.ndim(f_gust) == 0:
            f_gust_b = float(f_gust)
        else:
            f_gust_b = np.asarray(f_gust, dtype=np.float32).reshape(1, 1, 1, nt)

        wind = self.reference_speed * v_ref_b * f_z_b * f_urban_b * f_gust_b
        wind = np.clip(wind, 0.0, None).astype(np.float32)
        self._wind_4d = wind
        return wind

    # ------------------------------------------------------------------ #
    # 在线查询（可插拔；满足约束 (2)：风只作查询属性，非搜索维度）
    # ------------------------------------------------------------------ #
    def sample_speed(
        self,
        ix: float, iy: float, iz: float, t_seconds: float,
    ) -> float:
        """在线查询风速：网格浮点索引 + 绝对飞行时间（秒）。

        对 z 与时间做线性插值；供未来 TD-RiskA* 直接取原始 V（如侧风风险）
        使用，不改变“t 由路径传播”的架构。
        """
        if self._wind_4d is None or self._grid is None or self._time_hours is None:
            raise RuntimeError("请先调用 build_wind_tensor() 构建张量。")
        nx, ny, nz, nt = self._wind_4d.shape
        ix = float(np.clip(ix, 0, nx - 1))
        iy = float(np.clip(iy, 0, ny - 1))
        iz = float(np.clip(iz, 0, nz - 1))
        t_hours = float(t_seconds) / 3600.0
        # z 插值
        z0 = int(np.floor(iz)); z1 = min(z0 + 1, nz - 1)
        wz = iz - z0
        # t 插值
        t_arr = self._time_hours
        if t_arr.size == 1:
            t_idx = 0.0; wt = 0.0
        else:
            t_idx = float(np.interp(t_hours, t_arr, np.arange(t_arr.size)))
            t0 = int(np.floor(t_idx)); t1 = min(t0 + 1, nt - 1)
            wt = t_idx - t0
        # x,y 最近邻（风场水平分辨率与网格一致）
        ixn, iyn = int(round(ix)), int(round(iy))
        sheet = self._wind_4d[ixn, iyn, :, :]  # (nz, nt)
        if wt == 0.0:
            zs = sheet[:, int(round(t_idx))] if t_arr.size > 1 else sheet[:, 0]
        else:
            zs0 = sheet[:, t0]; zs1 = sheet[:, t1]
            zs = zs0 * (1 - wt) + zs1 * wt
        return float(zs[z0] * (1 - wz) + zs[z1] * wz)

    # ------------------------------------------------------------------ #
    # 元数据
    # ------------------------------------------------------------------ #
    def get_metadata(self) -> Dict:
        return {
            "model": self.kind,
            "scenario": self.scenario_name,
            "reference_speed": self.reference_speed,
            "mode": self.mode,
            "temporal_variation": self.temporal_enabled,
            "temporal_amplitude": self.temporal_amplitude,
            "temporal_period_hours": self.temporal_period_hours,
            "vertical_modifier": self.vertical_enabled,
            "vertical_min_factor": self.vertical_min,
            "vertical_max_factor": self.vertical_max,
            "urban_modifier": self.urban_enabled,
            "urban_beta": self.urban_beta,
            "urban_min_factor": self.urban_min,
            "urban_max_factor": self.urban_max,
            "gust_enabled": self.gust_enabled,
            "gust_rho": self.gust_rho,
            "gust_sigma": self.gust_sigma,
            "gust_seed": self.gust_seed,
            "unit": "m/s",
            "is_observed": False,
            "note": (
                "Scenario-based low-altitude wind environment. NOT a real/reconstructed "
                "micro-scale urban wind field. Do not treat as observational data."
            ),
        }

    # ------------------------------------------------------------------ #
    # 落盘
    # ------------------------------------------------------------------ #
    def save(self, tensors_dir: Union[str, Path], data_type: str = "synthetic") -> Dict:
        """保存 wind_speed_4d.npy 与 wind_environment_metadata.json。"""
        if self._wind_4d is None or self._grid is None:
            raise RuntimeError("请先调用 build_wind_tensor()。")
        tensors_dir = Path(tensors_dir)
        out_dir = tensors_dir / data_type if data_type else tensors_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        wind_path = out_dir / "wind_speed_4d.npy"
        meta_path = out_dir / "wind_environment_metadata.json"
        np.save(wind_path, self._wind_4d)
        import json
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.get_metadata(), f, indent=2, ensure_ascii=False)
        return {"wind_path": str(wind_path), "meta_path": str(meta_path)}


# ----------------------------------------------------------------------------
# 工厂：可插拔入口
# ----------------------------------------------------------------------------
def get_wind_environment(
    config: Optional[Union[dict, object]] = None,
    scenario_name: Optional[str] = None,
) -> WindEnvironment:
    """根据配置返回风环境实例。

    当前仅支持 scenario 模式；未来新增模式在此分支注册即可。
    """
    mode = _cfg_get(config, "mode", default="scenario")
    if mode == "scenario":
        return ScenarioWindEnvironment(config=config, scenario_name=scenario_name)
    raise ValueError(f"不支持的风环境模式：'{mode}'（当前仅支持 'scenario'）")
