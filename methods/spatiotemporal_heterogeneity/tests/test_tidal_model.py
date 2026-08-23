"""潮汐模型测试：质量守恒、Partition of Unity、单调性"""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig, get_micro_grid,
)
from methods.spatiotemporal_heterogeneity.src.data_provision.spatiotemporal_tidal_model import (
    SpatiotemporalTidalModel, TidalModelConfig,
)
from methods.spatiotemporal_heterogeneity.src.data_provision.poi_parser import (
    POI_CATEGORIES, create_synthetic_poi_counts,
)
from methods.spatiotemporal_heterogeneity.src.data_provision.population_resampler import (
    create_synthetic_base_population,
)


class TestTidalModelMassConservation(unittest.TestCase):
    """质量守恒：sum_i rho(i,t) * S_cell = N_total 对所有 t 成立"""

    def setUp(self):
        self.grid = GridSystem(
            spatial=SpatialGridConfig(nx=20, ny=20, nz=6, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=24, dt_minutes=60.0),
        )
        self.config = TidalModelConfig(N_total_pop=10000.0, N_total_veh=3000.0)
        self.model = SpatiotemporalTidalModel(grid=self.grid, config=self.config)

    def test_population_mass_conservation(self):
        """人口密度质量守恒误差 < 1%"""
        nx, ny = self.grid.spatial.nx, self.grid.spatial.ny
        landuse = np.random.randint(0, 7, (nx, ny)).astype(np.int32)
        base_pop = np.ones((nx, ny), dtype=np.float32) * 100
        poi_counts = create_synthetic_poi_counts(grid=self.grid, landuse=landuse, save=False)

        rho_pop = self.model.build_population_density(base_pop, poi_counts)
        check = self.model.verify_mass_conservation(rho_pop, self.config.N_total_pop, "population")

        self.assertLess(check["relative_error_max"], 0.01,
                        f"Population mass conservation violated: {check}")

    def test_vehicle_mass_conservation(self):
        """车辆密度质量守恒误差 < 1%"""
        nx, ny = self.grid.spatial.nx, self.grid.spatial.ny
        landuse = np.random.randint(0, 7, (nx, ny)).astype(np.int32)
        base_pop = np.ones((nx, ny), dtype=np.float32) * 100
        poi_counts = create_synthetic_poi_counts(grid=self.grid, landuse=landuse, save=False)

        rho_veh = self.model.build_vehicle_density(base_pop, poi_counts)
        check = self.model.verify_mass_conservation(rho_veh, self.config.N_total_veh, "vehicle")

        self.assertLess(check["relative_error_max"], 0.01,
                        f"Vehicle mass conservation violated: {check}")

    def test_density_non_negative(self):
        """密度值必须 >= 0"""
        nx, ny = self.grid.spatial.nx, self.grid.spatial.ny
        landuse = np.random.randint(0, 7, (nx, ny)).astype(np.int32)
        base_pop = np.ones((nx, ny), dtype=np.float32) * 100
        poi_counts = create_synthetic_poi_counts(grid=self.grid, landuse=landuse, save=False)

        rho_pop = self.model.build_population_density(base_pop, poi_counts)
        self.assertTrue(np.all(rho_pop >= 0), "Negative density found")


class TestPartitionOfUnity(unittest.TestCase):
    """时间激活函数 Partition of Unity：sum_theta phi_theta(t) = 1"""

    def setUp(self):
        self.model = SpatiotemporalTidalModel()

    def test_population_activation_sums_to_one(self):
        """人口激活函数对所有类别求和 = 1"""
        for hour in [0, 6, 8, 12, 14, 18, 20, 23]:
            phi = self.model._population_activation_all(float(hour))
            total = sum(phi.values())
            self.assertAlmostEqual(total, 1.0, places=6,
                                   msg=f"Population activation sum={total} at hour={hour}")

    def test_traffic_activation_sums_to_one(self):
        """交通激活函数对所有类别求和 = 1"""
        for hour in [0, 6, 8, 12, 14, 18, 20, 23]:
            phi = self.model._traffic_activation_all(float(hour))
            total = sum(phi.values())
            self.assertAlmostEqual(total, 1.0, places=6,
                                   msg=f"Traffic activation sum={total} at hour={hour}")

    def test_activation_in_unit_interval(self):
        """每个类别的激活值在 [0, 1] 范围内"""
        for hour in range(24):
            phi = self.model._population_activation_all(float(hour))
            for cat, val in phi.items():
                self.assertGreaterEqual(val, 0.0, f"{cat} negative at hour={hour}")
                self.assertLessEqual(val, 1.0, f"{cat} > 1 at hour={hour}")


class TestHuffGravity(unittest.TestCase):
    """Huff 引力场：归一化后 sum = 1"""

    def test_influence_maps_normalized(self):
        """每个类别的影响力图归一化后求和 = 1"""
        grid = GridSystem(
            spatial=SpatialGridConfig(nx=15, ny=15, nz=3, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=12, dt_minutes=60.0),
        )
        model = SpatiotemporalTidalModel(grid=grid)
        nx, ny = grid.spatial.nx, grid.spatial.ny
        landuse = np.random.randint(0, 7, (nx, ny)).astype(np.int32)
        poi_counts = create_synthetic_poi_counts(grid=grid, landuse=landuse, save=False)

        sigma_m = model.config.population_sigma_m
        maps = model.build_huff_influence_maps(poi_counts, sigma_m)

        for cat, m in maps.items():
            total = float(m.sum())
            if total > 0:  # skip empty categories
                self.assertAlmostEqual(total, 1.0, places=5,
                                       msg=f"{cat} influence map sum={total}")


if __name__ == "__main__":
    unittest.main()
