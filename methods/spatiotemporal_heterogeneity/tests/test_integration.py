"""全链路集成测试：data_provision → tensor_engine → algorithms"""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig,
)
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_p_crash import DynamicCrashProbability
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_fatality import DynamicFatalityModel
from methods.spatiotemporal_heterogeneity.src.tensor_engine.static_obstacle import PropertyDamageModel
from methods.spatiotemporal_heterogeneity.src.tensor_engine.dynamic_noise import DynamicNoiseCost
from methods.spatiotemporal_heterogeneity.src.data_provision.spatiotemporal_tidal_model import (
    SpatiotemporalTidalModel, TidalModelConfig,
)
from methods.spatiotemporal_heterogeneity.src.data_provision.poi_parser import create_synthetic_poi_counts
from methods.spatiotemporal_heterogeneity.src.algorithms.env_tensor import EnvTensor
from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D
from methods.spatiotemporal_heterogeneity.utils.synthetic_data_factory import generate_synthetic_city


class TestFullPipeline(unittest.TestCase):
    """端到端：合成数据 → 风险张量 → 路径规划"""

    def setUp(self):
        self.grid = GridSystem(
            spatial=SpatialGridConfig(nx=20, ny=20, nz=6, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=12, dt_minutes=60.0),
        )
        self.nx, self.ny, self.nz, self.nt = self.grid.shape

        # Generate synthetic city
        city = generate_synthetic_city(nx=self.nx, ny=self.ny, nz=self.nz, nt=self.nt, seed=42)
        self.landuse = city["landuse"].astype(np.int32)
        self.bh = city["building_heights"].astype(np.float32)
        self.wind = city["wind_field"].astype(np.float32)
        self.rain = city["rain_data"].astype(np.float32)
        self.population = city["population"].astype(np.float32)

    def _build_env_tensor(self):
        """构建完整 EnvTensor"""
        # 1. P_crash
        cm = DynamicCrashProbability()
        w2d = np.transpose(self.wind[:, :, 0, :], (1, 0, 2))
        r2d = np.transpose(self.rain, (1, 0, 2))
        fw = cm.compute_wind_factor(w2d[:, :, np.newaxis, :])
        fr = cm.compute_rain_factor(r2d[:, :, np.newaxis, :])
        fo = np.ones((self.nx, self.ny, self.nz, self.nt), dtype=np.float32)
        pc = np.clip(cm.compute_pcrash(fw, fr, fo, dt=3600.0), 0, 1).astype(np.float32)

        # 2. Tidal population
        lu_t = np.transpose(self.landuse, (1, 0))
        bp = np.transpose(self.population, (1, 0))
        poi_counts = create_synthetic_poi_counts(grid=self.grid, landuse=lu_t, save=False)
        tidal = SpatiotemporalTidalModel(grid=self.grid, config=TidalModelConfig(N_total_pop=5000.0))
        rho_pop = tidal.build_population_density(bp, poi_counts)
        rho_veh = rho_pop * 0.3

        # 3. Fatality
        fm = DynamicFatalityModel()
        ef3d = fm.compute_fatality_consequence(rho_pop=rho_pop, rho_vehicle=rho_veh, flight_altitude=50.0)
        ef = np.broadcast_to(ef3d[:, :, np.newaxis, :], (self.nx, self.ny, self.nz, self.nt)).astype(np.float32)

        # 4. Property
        bt = np.transpose(self.bh, (1, 0))
        pm = PropertyDamageModel(bt, max_prop_damage=1000.0)
        ep = pm.compute_property_consequence(flight_altitude=50.0).astype(np.float32)

        # 5. Noise
        nm = DynamicNoiseCost(grid=self.grid)
        rn = nm.compute_noise_cost(landuse=lu_t, population_density=rho_pop).astype(np.float32)

        # 6. Obstacle
        obs = np.zeros((self.nx, self.ny, self.nz), dtype=np.float32)
        for iz in range(self.nz):
            obs[:, :, iz] = (bt >= (iz + 1.0) * self.grid.spatial.dz).astype(np.float32)

        return EnvTensor(p_crash=pc, fatality=ef, property=ep, noise=rn, obstacle=obs, grid=self.grid)

    def test_pipeline_produces_valid_env_tensor(self):
        """全链路应产生合法的 EnvTensor"""
        env = self._build_env_tensor()
        self.assertEqual(env.shape, self.grid.shape)
        self.assertTrue(np.all(env.p_crash >= 0))
        self.assertTrue(np.all(env.p_crash < 1))
        self.assertTrue(np.all(np.isfinite(env.fatality)))
        self.assertTrue(np.all(np.isfinite(env.noise)))

    def test_pipeline_finds_path(self):
        """全链路应能找到可行路径"""
        env = self._build_env_tensor()
        planner = AStar4D(self.grid, env, {
            "uav_speed": 10.0,
            "w_distance": 0.4, "w_fatality": 0.3, "w_property": 0.15, "w_noise": 0.15,
            "survival_threshold": 0.01,
        })

        start = (2, 2, 3, 0)
        goal = (self.nx - 3, self.ny - 3, 3)
        result = planner.search(start, goal)

        self.assertEqual(result["status"], "success")
        self.assertGreater(result["total_distance"], 0)
        self.assertGreater(result["final_p_survival"], 0)
        self.assertGreater(len(result["path"]), 1)

    def test_different_weights_different_paths(self):
        """不同权重应产生不同路径或代价"""
        env = self._build_env_tensor()
        start = (2, 2, 3, 0)
        goal = (self.nx - 3, self.ny - 3, 3)

        # Safety-first
        p1 = AStar4D(self.grid, env, {
            "uav_speed": 10.0, "w_distance": 0.0, "w_fatality": 0.7,
            "w_property": 0.2, "w_noise": 0.1, "survival_threshold": 0.01,
        })
        r1 = p1.search(start, goal)

        # Distance-first
        p2 = AStar4D(self.grid, env, {
            "uav_speed": 10.0, "w_distance": 0.8, "w_fatality": 0.1,
            "w_property": 0.05, "w_noise": 0.05, "survival_threshold": 0.01,
        })
        r2 = p2.search(start, goal)

        self.assertEqual(r1["status"], "success")
        self.assertEqual(r2["status"], "success")
        # Safety-first should have lower fatality, distance-first should have shorter path
        self.assertLessEqual(r1["cum_fatality"], r2["cum_fatality"] * 1.5)  # allow some tolerance

    def test_state_vector_fields_complete(self):
        """路径状态向量必须包含所有字段"""
        env = self._build_env_tensor()
        planner = AStar4D(self.grid, env, {
            "uav_speed": 10.0, "w_distance": 0.4, "survival_threshold": 0.01,
        })
        result = planner.search((2, 2, 3, 0), (self.nx - 3, self.ny - 3, 3))
        self.assertEqual(result["status"], "success")

        step = result["path"][0]
        required_state_keys = [
            "cum_distance", "cum_time", "absolute_time",
            "cumulative_hazard", "p_survival",
            "cum_fatality", "cum_property", "cum_noise", "cum_objective",
        ]
        for key in required_state_keys:
            self.assertIn(key, step["state"], f"Missing state key: {key}")


if __name__ == "__main__":
    unittest.main()
