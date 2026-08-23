"""合成数据工厂测试：确定性、完整性、约束验证"""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.utils.synthetic_data_factory import (
    generate_synthetic_city,
)


class TestSyntheticDataDeterminism(unittest.TestCase):
    """相同 seed 必须产生完全相同的数据"""

    def test_same_seed_same_result(self):
        """seed=42 两次生成应完全一致"""
        data1 = generate_synthetic_city(nx=20, ny=20, nz=6, nt=12, seed=42)
        data2 = generate_synthetic_city(nx=20, ny=20, nz=6, nt=12, seed=42)

        np.testing.assert_array_equal(data1["landuse"], data2["landuse"])
        np.testing.assert_array_equal(data1["road_mask"], data2["road_mask"])
        np.testing.assert_array_equal(data1["building_heights"], data2["building_heights"])
        np.testing.assert_array_equal(data1["population"], data2["population"])
        np.testing.assert_array_equal(data1["wind_field"], data2["wind_field"])
        np.testing.assert_array_equal(data1["rain_data"], data2["rain_data"])

    def test_different_seed_different_result(self):
        """不同 seed 应产生不同数据"""
        data1 = generate_synthetic_city(nx=20, ny=20, nz=6, nt=12, seed=42)
        data2 = generate_synthetic_city(nx=20, ny=20, nz=6, nt=12, seed=123)

        # At least one array should differ
        differs = False
        for key in ["landuse", "building_heights", "wind_field"]:
            if not np.array_equal(data1[key], data2[key]):
                differs = True
                break
        self.assertTrue(differs, "Different seeds produced identical data")


class TestSyntheticDataCompleteness(unittest.TestCase):
    """生成的数据必须包含所有必需字段"""

    def test_all_fields_present(self):
        """必须返回所有规定字段"""
        data = generate_synthetic_city(nx=15, ny=15, nz=4, nt=8, seed=42)
        required = ["landuse", "road_mask", "building_heights", "poi",
                     "population", "wind_field", "rain_data", "od_pairs"]
        for key in required:
            self.assertIn(key, data, f"Missing field: {key}")

    def test_poi_has_five_categories(self):
        """POI 必须包含 5 个类别"""
        data = generate_synthetic_city(nx=15, ny=15, nz=4, nt=8, seed=42)
        expected_cats = {"residential", "office", "institution", "transport", "industrial"}
        self.assertEqual(set(data["poi"].keys()), expected_cats)

    def test_shapes_match_dimensions(self):
        """数组形状必须与指定维度一致"""
        nx, ny, nz, nt = 15, 15, 4, 8
        data = generate_synthetic_city(nx=nx, ny=ny, nz=nz, nt=nt, seed=42)

        self.assertEqual(data["landuse"].shape, (ny, nx))
        self.assertEqual(data["road_mask"].shape, (ny, nx))
        self.assertEqual(data["building_heights"].shape, (ny, nx))
        self.assertEqual(data["population"].shape, (ny, nx))
        self.assertEqual(data["wind_field"].shape, (ny, nx, nz, nt))
        self.assertEqual(data["rain_data"].shape, (ny, nx, nt))
        for cat, arr in data["poi"].items():
            self.assertEqual(arr.shape, (ny, nx), f"POI {cat} shape mismatch")


class TestSyntheticDataConstraints(unittest.TestCase):
    """数据约束验证"""

    def setUp(self):
        self.data = generate_synthetic_city(nx=20, ny=20, nz=6, nt=12, seed=42)

    def test_landuse_values_in_range(self):
        """土地利用值在 1-6 范围内"""
        lu = self.data["landuse"]
        self.assertTrue(np.all(lu >= 1))
        self.assertTrue(np.all(lu <= 6))

    def test_building_heights_non_negative(self):
        """建筑高度 >= 0"""
        self.assertTrue(np.all(self.data["building_heights"] >= 0))

    def test_population_non_negative(self):
        """人口密度 >= 0"""
        self.assertTrue(np.all(self.data["population"] >= 0))

    def test_wind_field_non_negative(self):
        """风速 >= 0"""
        self.assertTrue(np.all(self.data["wind_field"] >= 0))

    def test_rain_non_negative(self):
        """降雨 >= 0"""
        self.assertTrue(np.all(self.data["rain_data"] >= 0))

    def test_road_mask_is_binary(self):
        """道路掩码是布尔值"""
        rm = self.data["road_mask"]
        self.assertTrue(np.all((rm == 0) | (rm == 1)))

    def test_poi_non_negative(self):
        """POI 密度 >= 0"""
        for cat, arr in self.data["poi"].items():
            self.assertTrue(np.all(arr >= 0), f"POI {cat} has negative values")

    def test_od_pairs_valid(self):
        """OD 对在网格范围内"""
        nx, ny = 20, 20
        for od in self.data["od_pairs"]:
            start, goal = od
            self.assertTrue(0 <= start[0] < nx and 0 <= start[1] < ny)
            self.assertTrue(0 <= goal[0] < nx and 0 <= goal[1] < ny)


if __name__ == "__main__":
    unittest.main()
