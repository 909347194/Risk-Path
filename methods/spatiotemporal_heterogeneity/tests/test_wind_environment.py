"""情景化低空风环境单元测试。

覆盖实现规格 §24 的 10 条要求，并补充 F_wind 单调性 / 配置容错 / 双计权约束验证。
"""
import os
import tempfile
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.wind_environment import (
    ScenarioWindEnvironment, get_wind_environment, WindEnvironment,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_p_crash import (
    DynamicCrashProbability,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.risk_tensor_assembler import (
    build_risk_tensors,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.config_manager import load_config


def make_grid(nx=8, ny=8, nz=4, nt=12):
    """小网格：总时长 12×120min = 24h，与 period_hours=24 对齐。"""
    return GridSystem(
        spatial=SpatialGridConfig(nx=nx, ny=ny, nz=nz, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=nt, dt_minutes=120.0),
    )


def make_building(nx=8, ny=8):
    """制造高度异质：一半高一半低，触发 SVF 差异。"""
    h = np.zeros((nx, ny), dtype=np.float32)
    h[: nx // 2, :] = 40.0
    h[nx // 2:, :] = 5.0
    return h


class TestWindEnvironmentShape(unittest.TestCase):
    """§24 Test 1–3：shape / dtype / 单位(m/s)。"""

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def test_shape(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertEqual(wind.shape, self.grid.shape)  # (nx, ny, nz, nt)

    def test_dtype(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertEqual(wind.dtype, np.float32)

    def test_unit_mps_nonnegative(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="strong")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertTrue(np.all(np.isfinite(wind)))
        self.assertTrue(np.all(wind >= 0.0))  # 风速单位为 m/s，非负


class TestWindEnvironmentFactors(unittest.TestCase):
    """§24 Test 4–7：高度趋势 / 时间变化 / 情景单调 / 城市边界。"""

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def _expected(self, env, gust_factor=None):
        V0 = env.reference_speed
        t = env._temporal_factor(env._resolve_time(self.grid, None))      # (nt,)
        fz = env._vertical_factor(self.grid.z_heights)                    # (nz,)
        fu = env._urban_shelter(self.building, None)                      # (nx, ny)
        fu4 = fu.reshape(self.grid.spatial.nx, self.grid.spatial.ny, 1, 1)
        ref = V0 * t.reshape(1, 1, 1, -1) * fz.reshape(1, 1, -1, 1) * fu4
        if gust_factor is not None:
            g = gust_factor if np.ndim(gust_factor) == 0 else gust_factor.reshape(1, 1, 1, -1)
            ref = ref * g
        return ref.astype(np.float32)

    def test_height_trend(self):
        """城市修正关闭时，V(z_max) > V(z_min)。"""
        cfg = {"urban_modifier": {"enabled": False}}
        env = ScenarioWindEnvironment(config=cfg, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertGreater(float(wind[:, :, -1, :].mean()), float(wind[:, :, 0, :].mean()))
        self.assertTrue(np.all(wind[:, :, -1, :] > wind[:, :, 0, :]))

    def test_temporal_variation(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertFalse(np.allclose(wind[:, :, :, 0], wind[:, :, :, self.grid.temporal.nt // 4]))

    def test_temporal_disabled_is_constant(self):
        cfg = {"temporal_variation": {"enabled": False}}
        env = ScenarioWindEnvironment(config=cfg, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        # 时间维度应为常数
        self.assertTrue(np.allclose(wind[:, :, :, 0], wind[:, :, :, 1]))

    def test_scenario_monotonicity(self):
        """相同 (x,y,z,t)：weak < moderate < strong。"""
        base = {"urban_modifier": {"enabled": False}, "temporal_variation": {"enabled": False}}
        w = ScenarioWindEnvironment(config=base, scenario_name="weak").build_wind_tensor(self.grid, self.building)
        m = ScenarioWindEnvironment(config=base, scenario_name="moderate").build_wind_tensor(self.grid, self.building)
        s = ScenarioWindEnvironment(config=base, scenario_name="strong").build_wind_tensor(self.grid, self.building)
        self.assertTrue(np.all(m > w))
        self.assertTrue(np.all(s > m))

    def test_urban_modifier_bounds(self):
        """min_factor <= F_urban <= max_factor。"""
        cfg = {"urban_modifier": {"enabled": True, "beta": 0.20, "min_factor": 0.80, "max_factor": 1.05}}
        env = ScenarioWindEnvironment(config=cfg, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        # 还原 F_urban = V / (V0 * temporal * vertical)
        t = env._temporal_factor(env._resolve_time(self.grid, None)).reshape(1, 1, 1, -1)
        fz = env._vertical_factor(self.grid.z_heights).reshape(1, 1, -1, 1)
        f_urban = wind / (env.reference_speed * t * fz)
        self.assertTrue(np.all(f_urban >= 0.80 - 1e-4))
        self.assertTrue(np.all(f_urban <= 1.05 + 1e-4))

    def test_urban_open_area_not_amplified(self):
        """开敞区 (SVF=1) → F_urban == 1.0（衰减而非放大，杜绝与 f_obs 同号双计权）。"""
        cfg = {"urban_modifier": {"enabled": True, "beta": 0.20}}
        env = ScenarioWindEnvironment(config=cfg, scenario_name="moderate")
        svf_open = np.ones((8, 8), dtype=np.float32)
        fu = env._urban_shelter(self.building, svf_open)
        self.assertTrue(np.allclose(fu, 1.0, atol=1e-5))


class TestWindEnvironmentGust(unittest.TestCase):
    """§24 Test 8–9：gust 复现 / 关闭。"""

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def test_gust_reproducible(self):
        cfg = {"gust": {"enabled": True, "seed": 42}}
        a = ScenarioWindEnvironment(config=cfg, scenario_name="moderate").build_wind_tensor(self.grid, self.building)
        b = ScenarioWindEnvironment(config=cfg, scenario_name="moderate").build_wind_tensor(self.grid, self.building)
        self.assertTrue(np.array_equal(a, b))

    def test_gust_seed_changes_series(self):
        c1 = {"gust": {"enabled": True, "seed": 42}}
        c2 = {"gust": {"enabled": True, "seed": 7}}
        a = ScenarioWindEnvironment(config=c1, scenario_name="moderate").build_wind_tensor(self.grid, self.building)
        b = ScenarioWindEnvironment(config=c2, scenario_name="moderate").build_wind_tensor(self.grid, self.building)
        self.assertFalse(np.allclose(a, b))

    def test_gust_disabled_equals_unity(self):
        """gust.enabled=false → F_gust=1，风 = V0·temporal·vertical·urban。"""
        cfg = {"gust": {"enabled": False}}
        env = ScenarioWindEnvironment(config=cfg, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        expected = self._expected_no_gust(env)
        self.assertTrue(np.allclose(wind, expected, atol=1e-3))

    def _expected_no_gust(self, env):
        V0 = env.reference_speed
        t = env._temporal_factor(env._resolve_time(self.grid, None)).reshape(1, 1, 1, -1)
        fz = env._vertical_factor(self.grid.z_heights).reshape(1, 1, -1, 1)
        fu = env._urban_shelter(self.building, None).reshape(self.grid.spatial.nx, self.grid.spatial.ny, 1, 1)
        return (V0 * t * fz * fu).astype(np.float32)


class TestWindLimitAndInterface(unittest.TestCase):
    """§24 Test 10：风极限 → F_wind=inf → P_crash_step=1；可插拔接口。"""

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def test_wind_limit_yields_unit_pcrash(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        # 制造一个超抗风极限的单元（common.yaml V_limit=12）
        wind = wind.copy()
        wind[0, 0, 0, 0] = 15.0
        model = DynamicCrashProbability()  # 默认 V_limit=12
        f_wind = model.compute_wind_factor(wind)
        self.assertTrue(np.isinf(f_wind[0, 0, 0, 0]))
        ones = np.ones_like(wind)
        p = model.compute_pcrash(f_wind, ones, ones, dt=60.0)
        self.assertEqual(float(p[0, 0, 0, 0]), 1.0)
        # 其余有限风速单元 p<1
        self.assertTrue(np.all(p[1:, ...] < 1.0))

    def test_f_wind_monotonic_below_limit(self):
        """V < V_limit 时 F_wind 随 V 单调递增（与 compute_wind_factor 兼容）。"""
        model = DynamicCrashProbability()
        vs = np.array([1.0, 3.0, 6.0, 9.0, 11.9], dtype=np.float32)
        fw = model.compute_wind_factor(vs)
        self.assertTrue(np.all(np.isfinite(fw)))
        self.assertTrue(np.all(np.diff(fw) > 0))

    def test_sample_speed_online_query(self):
        """sample_speed 在线查询返回有限风速（风作状态属性，非搜索维度）。"""
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        v = env.sample_speed(ix=2.3, iy=4.1, iz=1.5, t_seconds=3600.0)
        self.assertTrue(np.isfinite(v))
        self.assertGreaterEqual(v, 0.0)


class TestConfigAndFactory(unittest.TestCase):
    """配置容错 / 工厂可插拔。"""

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def test_defaults_without_config(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        self.assertAlmostEqual(env.reference_speed, 6.0)
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertEqual(wind.shape, self.grid.shape)

    def test_load_from_common_yaml(self):
        cfg = load_config()  # 直接返回 common.yaml 内容（EasyDict），无 .common 包装
        env = get_wind_environment(cfg.wind_environment, scenario_name="moderate")
        self.assertIsInstance(env, WindEnvironment)
        self.assertEqual(env.mode, "scenario")
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        self.assertEqual(wind.shape, self.grid.shape)

    def test_metadata_is_observed_false(self):
        env = ScenarioWindEnvironment(config=None, scenario_name="moderate")
        env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        meta = env.get_metadata()
        self.assertFalse(meta["is_observed"])
        self.assertEqual(meta["model"], "scenario_based_low_altitude_wind_environment")


class TestWindConfigSectionHonored(unittest.TestCase):
    """回归（审查 HIGH 项）：传入 wind_environment *节* 时，自定义参数必须生效。

    这直接守卫 get_wind_environment 的契约——若将来又有人把路径字符串当 config 传入，
    自定义值会被静默忽略，本测试应失败。
    """

    def setUp(self):
        self.grid = make_grid()
        self.building = make_building()

    def _section(self, amplitude):
        return {
            "mode": "scenario",
            "scenarios": {"weak": 3.0, "moderate": 6.0, "strong": 9.0},
            "default_scenario": "moderate",
            "temporal_variation": {"enabled": True, "amplitude": amplitude, "period_hours": 24.0, "phase": 0.0},
            "vertical_profile": {"enabled": True, "min_factor": 0.85, "max_factor": 1.20},
            "urban_modifier": {"enabled": True, "beta": 0.20, "min_factor": 0.80, "max_factor": 1.05},
            "gust": {"enabled": False},
        }

    def test_custom_temporal_amplitude_honored(self):
        env = get_wind_environment(self._section(0.9), scenario_name="moderate")
        # 直接的契约断言：自定义 amplitude 必须被读取
        self.assertAlmostEqual(env.temporal_amplitude, 0.9, places=6)
        wind = env.build_wind_tensor(grid=self.grid, building_heights=self.building)
        # 开敞低层单元沿时间的相对摆动应反映 amplitude（采样峰略低于 0.9）
        i = self.grid.spatial.nx // 2
        series = wind[i, 0, 0, :]
        rel = series / series.mean() - 1.0
        self.assertGreater(float(rel.max()), 0.8)  # 远超默认 0.15

    def test_section_not_path(self):
        """反例守卫：传入路径字符串时 get_wind_environment 应回退默认（而非崩溃）。"""
        env = get_wind_environment(str(Path(__file__).resolve().parents[1] / "configs" / "common.yaml"))
        self.assertAlmostEqual(env.temporal_amplitude, 0.15, places=6)  # 默认振幅


class TestBuildRiskTensorsWindConfig(unittest.TestCase):
    """回归（审查 HIGH 项）：build_risk_tensors 必须加载实验配置并把 wind_environment 节
    传给风环境——否则每个实验自己的风场配置不会生效。

    用一份临时“实验配置”yaml（amplitude=0.9）对比默认 common.yaml（amplitude=0.15），
    断言 p_crash 沿时间维度的标准差随振幅增大而增大（风场已真正受配置驱动）。

    注：噪声模型内部写死默认网格 (60,60,12,96)，故本测试使用默认网格以匹配其形状。
    """

    def setUp(self):
        self.grid = GridSystem()  # 默认 60×60×12×96，与噪声模型内部网格一致
        self.building = make_building(self.grid.spatial.nx, self.grid.spatial.ny)

    def _fake_result(self):
        nx, ny, nz, nt = self.grid.shape

        class _R:
            pass

        r = _R()
        r.landuse = np.zeros((nx, ny), np.float32)
        r.building_heights = self.building.astype(np.float32)
        r.rho_population = np.full((nx, ny, nt), 0.05, np.float32)
        r.rho_vehicle = np.full((nx, ny, nt), 0.05, np.float32)
        r.wind_field = np.zeros((nx, ny, nt), np.float32)   # scenario 模式忽略
        r.rain_data = np.zeros((nx, ny, nt), np.float32)
        return r

    def _write_custom_cfg(self, amplitude):
        text = (
            "wind_environment:\n"
            "  mode: scenario\n"
            "  scenarios: {weak: 3.0, moderate: 6.0, strong: 9.0}\n"
            "  default_scenario: moderate\n"
            "  temporal_variation: {enabled: true, amplitude: %s, period_hours: 24.0, phase: 0.0}\n"
            "  vertical_profile: {enabled: true, min_factor: 0.85, max_factor: 1.20}\n"
            "  urban_modifier: {enabled: true, beta: 0.20, min_factor: 0.80, max_factor: 1.05}\n"
            "  gust: {enabled: false}\n"
        ) % amplitude
        fd = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w", encoding="utf-8")
        fd.write(text)
        fd.close()
        return fd.name

    def test_pipeline_honors_experiment_wind_config(self):
        result = self._fake_result()
        t_def = build_risk_tensors(result, grid=self.grid, config_path=None)  # common.yaml：0.15
        cfg_path = self._write_custom_cfg(0.9)
        try:
            t_cus = build_risk_tensors(result, grid=self.grid, config_path=cfg_path)  # 实验：0.9
        finally:
            os.remove(cfg_path)
        # 风场时间摆动更大 → p_crash 沿时间维度的标准差更大
        std_def = float(np.mean(t_def["p_crash"].std(axis=3)))
        std_cus = float(np.mean(t_cus["p_crash"].std(axis=3)))
        self.assertGreater(std_cus, std_def)


if __name__ == "__main__":
    unittest.main(verbosity=2)
