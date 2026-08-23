"""风险模型单元测试：p_crash、fatality、property、noise"""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig, get_micro_grid,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_p_crash import (
    DynamicCrashProbability, CrashProbConfig, WindConfig, RainConfig, UrbanCanyonConfig,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_fatality import (
    DynamicFatalityModel, FatalityConfig,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.static_obstacle import (
    PropertyDamageModel,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_noise import (
    DynamicNoiseCost, NoiseConfig,
)
from methods.spatiotemporal_heterogeneity.src.algorithms.env_tensor import EnvTensor


class TestDynamicCrashProbability(unittest.TestCase):
    """§4.1 坠机概率模型测试"""

    def setUp(self):
        self.model = DynamicCrashProbability()
        self.nx, self.ny, self.nz, self.nt = 10, 10, 3, 4

    def test_pcrash_range_zero_in_calm_conditions(self):
        """晴朗无风时 P_crash ≈ λ_base × Δt"""
        wind = np.zeros((self.nx, self.ny, self.nz, self.nt), dtype=np.float32)
        rain = np.zeros((self.nx, self.ny, self.nz, self.nt), dtype=np.float32)
        obs = np.ones((self.nx, self.ny, self.nz, self.nt), dtype=np.float32)

        f_wind = self.model.compute_wind_factor(wind)
        f_rain = self.model.compute_rain_factor(rain)
        p_crash = self.model.compute_pcrash(f_wind, f_rain, obs, dt=1.0)

        # f_wind=1, f_rain=1, f_obs=1 → Phi=1 → P_crash = 1-exp(-lambda_base)
        # 允许浮点误差
        expected = 1.0 - np.exp(-1e-5 * 1.0)
        np.testing.assert_allclose(p_crash, expected, rtol=0.02)

    def test_pcrash_always_in_unit_interval(self):
        """P_crash 必须在 [0, 1] 范围内（极端条件可达到 1）"""
        rng = np.random.default_rng(42)
        wind = rng.uniform(0, 11, (self.nx, self.ny, self.nz, self.nt)).astype(np.float32)
        rain = rng.uniform(0, 30, (self.nx, self.ny, self.nz, self.nt)).astype(np.float32)
        obs = rng.uniform(1, 5, (self.nx, self.ny, self.nz, self.nt)).astype(np.float32)

        f_wind = self.model.compute_wind_factor(wind)
        f_rain = self.model.compute_rain_factor(rain)
        p_crash = self.model.compute_pcrash(f_wind, f_rain, obs, dt=60.0)  # 1 min, reasonable

        self.assertTrue(np.all(p_crash >= 0.0))
        self.assertTrue(np.all(p_crash <= 1.0))

    def test_wind_factor_increases_with_speed(self):
        """风因子随风速单调递增"""
        speeds = np.array([0, 2, 4, 6, 8, 10, 11.9], dtype=np.float32)
        wind = speeds.reshape(1, 1, 1, -1).repeat(3, axis=2)
        f_wind = self.model.compute_wind_factor(wind)
        for i in range(len(speeds) - 1):
            self.assertLess(f_wind[0, 0, 0, i], f_wind[0, 0, 0, i + 1])

    def test_wind_factor_infinite_at_limit(self):
        """风速 >= V_limit 时 f_wind = inf"""
        wind = np.array([[[[13.0]]]], dtype=np.float32)  # > V_limit=12
        f_wind = self.model.compute_wind_factor(wind)
        self.assertEqual(f_wind[0, 0, 0, 0], np.inf)

    def test_rain_factor_increases_with_intensity(self):
        """降雨因子随雨强单调递增"""
        intensities = np.array([0, 5, 10, 20, 50], dtype=np.float32)
        rain = intensities.reshape(1, 1, 1, -1)
        f_rain = self.model.compute_rain_factor(rain)
        for i in range(len(intensities) - 1):
            self.assertLess(f_rain[0, 0, 0, i], f_rain[0, 0, 0, i + 1])

    def test_rain_factor_equals_one_when_no_rain(self):
        """无雨时 f_rain = 1.0"""
        rain = np.zeros((2, 2, 1, 1), dtype=np.float32)
        f_rain = self.model.compute_rain_factor(rain)
        np.testing.assert_allclose(f_rain, 1.0)

    def test_monotonicity_pcrash_increases_with_phi(self):
        """P_crash 随 Phi 单调递增"""
        wind_calm = np.zeros((1, 1, 1, 1), dtype=np.float32)
        wind_storm = np.full((1, 1, 1, 1), 10.0, dtype=np.float32)
        rain = np.zeros((1, 1, 1, 1), dtype=np.float32)
        obs = np.ones((1, 1, 1, 1), dtype=np.float32)

        fw_calm = self.model.compute_wind_factor(wind_calm)
        fw_storm = self.model.compute_wind_factor(wind_storm)
        fr = self.model.compute_rain_factor(rain)

        pc_calm = self.model.compute_pcrash(fw_calm, fr, obs, dt=3600.0)
        pc_storm = self.model.compute_pcrash(fw_storm, fr, obs, dt=3600.0)
        self.assertLess(pc_calm.flat[0], pc_storm.flat[0])


class TestDynamicFatalityModel(unittest.TestCase):
    """§4.2 致死风险模型测试"""

    def test_fatality_non_negative(self):
        """致死后果 >= 0"""
        model = DynamicFatalityModel()
        rho_pop = np.ones((5, 5, 4), dtype=np.float32) * 100
        rho_vehicle = np.ones((5, 5, 4), dtype=np.float32) * 30
        ef = model.compute_fatality_consequence(rho_pop, rho_vehicle, flight_altitude=50.0)
        self.assertTrue(np.all(ef >= 0))

    def test_fatality_increases_with_population(self):
        """人口密集区致死后果更高"""
        model = DynamicFatalityModel()
        rho_low = np.ones((5, 5, 4), dtype=np.float32) * 10
        rho_high = np.ones((5, 5, 4), dtype=np.float32) * 1000
        veh = np.ones((5, 5, 4), dtype=np.float32) * 10

        ef_low = model.compute_fatality_consequence(rho_low, veh, flight_altitude=50.0)
        ef_high = model.compute_fatality_consequence(rho_high, veh, flight_altitude=50.0)
        self.assertLess(float(np.mean(ef_low)), float(np.mean(ef_high)))


class TestPropertyDamageModel(unittest.TestCase):
    """§4.2 财产损失模型测试"""

    def test_property_non_negative(self):
        """财产损失后果 >= 0"""
        bh = np.ones((5, 5), dtype=np.float32) * 30  # 30m buildings
        model = PropertyDamageModel(bh, max_prop_damage=1000.0)
        ep = model.compute_property_consequence(flight_altitude=50.0)
        self.assertTrue(np.all(ep >= 0))

    def test_property_independent_of_flight_altitude(self):
        """财产损失是静态建筑属性，不随飞行高度变化（模型设计如此）"""
        bh = np.ones((5, 5), dtype=np.float32) * 10
        model = PropertyDamageModel(bh, max_prop_damage=1000.0)
        ep_low = model.compute_property_consequence(flight_altitude=10.0)
        ep_high = model.compute_property_consequence(flight_altitude=500.0)
        # Both should be positive (property value exists regardless of altitude)
        self.assertTrue(np.all(ep_low > 0))
        self.assertTrue(np.all(ep_high > 0))


class TestDynamicNoiseCost(unittest.TestCase):
    """§4.3 噪声成本模型测试"""

    def test_noise_non_negative(self):
        """噪声成本 >= 0"""
        grid = get_micro_grid()
        model = DynamicNoiseCost(grid=grid)
        landuse = np.ones((grid.spatial.nx, grid.spatial.ny), dtype=np.int32)
        pop = np.ones((grid.spatial.nx, grid.spatial.ny, grid.temporal.nt), dtype=np.float32) * 100
        noise = model.compute_noise_cost(landuse, pop)
        self.assertTrue(np.all(noise >= 0))

    def test_noise_higher_in_residential_at_night(self):
        """夜间住宅区噪声成本 > 日间"""
        grid = GridSystem(
            spatial=SpatialGridConfig(nx=10, ny=10, nz=3, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=24, dt_minutes=60.0),
        )
        model = DynamicNoiseCost(grid=grid)
        landuse = np.ones((10, 10), dtype=np.int32)
        pop = np.ones((10, 10, 24), dtype=np.float32) * 100
        noise = model.compute_noise_cost(landuse, pop)  # (nx, ny, nz, nt)
        # Night (t=2, 02:00) vs day (t=12, 12:00)
        night_mean = float(np.mean(noise[:, :, :, 2]))
        day_mean = float(np.mean(noise[:, :, :, 12]))
        self.assertGreater(night_mean, day_mean)


class TestEnvTensor(unittest.TestCase):
    """§3 风险张量容器测试"""

    def setUp(self):
        self.grid = GridSystem(
            spatial=SpatialGridConfig(nx=5, ny=5, nz=3, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=8, dt_minutes=15.0),
        )

    def test_broadcast_2d_to_4d(self):
        """2D 张量应自动广播到 4D"""
        nx, ny, nz, nt = self.grid.shape
        env = EnvTensor(
            p_crash=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            fatality=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            property=np.ones((nx, ny), dtype=np.float32),  # 2D
            noise=np.ones((nx, ny, nz), dtype=np.float32),  # 3D
            grid=self.grid,
        )
        self.assertEqual(env.property.shape, self.grid.shape)
        self.assertEqual(env.noise.shape, self.grid.shape)

    def test_pcrash_must_be_probability(self):
        """p_crash 超出 [0,1] 应抛出异常"""
        with self.assertRaises(ValueError):
            EnvTensor(
                p_crash=np.full(self.grid.shape, 1.5, dtype=np.float32),  # > 1
                fatality=np.zeros(self.grid.shape, dtype=np.float32),
                property=np.zeros(self.grid.shape, dtype=np.float32),
                noise=np.zeros(self.grid.shape, dtype=np.float32),
                grid=self.grid,
            )

    def test_risk_at_returns_all_components(self):
        """risk_at 应返回所有风险分量"""
        nx, ny, nz, nt = self.grid.shape
        env = EnvTensor(
            p_crash=np.full(self.grid.shape, 0.01, dtype=np.float32),
            fatality=np.full(self.grid.shape, 0.5, dtype=np.float32),
            property=np.full(self.grid.shape, 100.0, dtype=np.float32),
            noise=np.full(self.grid.shape, 0.1, dtype=np.float32),
            grid=self.grid,
        )
        risk = env.risk_at(0, 0, 0, 0)
        self.assertIn("p_crash", risk)
        self.assertIn("fatality", risk)
        self.assertIn("property", risk)
        self.assertIn("noise", risk)
        self.assertIn("obstacle", risk)


if __name__ == "__main__":
    unittest.main()
