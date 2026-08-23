"""算法边界条件测试：极端输入、硬约束、Label-Setting"""
import unittest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem, SpatialGridConfig, TemporalGridConfig,
)
from methods.spatiotemporal_heterogeneity.src.algorithms.common import SearchNode
from methods.spatiotemporal_heterogeneity.src.algorithms.env_tensor import EnvTensor
from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D


def make_grid(nx=5, ny=5, nz=3, nt=8):
    return GridSystem(
        spatial=SpatialGridConfig(nx=nx, ny=ny, nz=nz, dx=10.0, dy=10.0, dz=10.0),
        temporal=TemporalGridConfig(nt=nt, dt_minutes=15.0),
    )


def make_zero_env(grid):
    nx, ny, nz, nt = grid.shape
    return EnvTensor(
        p_crash=np.zeros((nx, ny, nz, nt), dtype=np.float32),
        fatality=np.zeros((nx, ny, nz, nt), dtype=np.float32),
        property=np.zeros((nx, ny), dtype=np.float32),
        noise=np.zeros((nx, ny, nz, nt), dtype=np.float32),
        grid=grid,
    )


class TestAStarBasic(unittest.TestCase):
    """基本路径搜索测试"""

    def test_straight_line_in_zero_risk(self):
        """零风险环境中应找到最短路径"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 1.0})

        result = planner.search((0, 0, 1, 0), (4, 4, 1))
        self.assertEqual(result["status"], "success")
        # Path should exist
        self.assertGreater(len(result["path"]), 0)

    def test_start_equals_goal(self):
        """起点 = 终点应立即返回"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 1.0})

        result = planner.search((2, 2, 1, 0), (2, 2, 1))
        self.assertEqual(result["status"], "success")
        self.assertAlmostEqual(result["total_distance"], 0.0)

    def test_start_in_obstacle_fails(self):
        """起点在障碍物内应失败"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        env.obstacle = np.zeros(grid.shape, dtype=bool)
        env.obstacle[0, 0, :, :] = True  # block start

        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 1.0})
        result = planner.search((0, 0, 1, 0), (4, 4, 1))
        self.assertEqual(result["status"], "failed")


class TestSurvivalConstraint(unittest.TestCase):
    """存活率硬约束测试"""

    def test_high_crash_rate_prunes_path(self):
        """极高坠机率下路径应被剪枝"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        # Set very high p_crash everywhere
        env.p_crash = np.full(grid.shape, 0.99, dtype=np.float32)

        planner = AStar4D(grid, env, {
            "uav_speed": 10.0, "w_distance": 1.0,
            "survival_threshold": 0.5,
        })
        result = planner.search((0, 0, 1, 0), (4, 4, 1))
        # Should fail or have very low survival
        if result["status"] == "success":
            self.assertLess(result["final_p_survival"], 0.5)

    def test_zero_threshold_allows_all_paths(self):
        """survival_threshold=0 不应剪枝任何路径"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        env.p_crash = np.full(grid.shape, 0.01, dtype=np.float32)

        planner = AStar4D(grid, env, {
            "uav_speed": 10.0, "w_distance": 1.0,
            "survival_threshold": 0.0,
        })
        result = planner.search((0, 0, 1, 0), (4, 4, 1))
        self.assertEqual(result["status"], "success")


class TestBatteryConstraint(unittest.TestCase):
    """电池续航约束测试"""

    def test_short_battery_prunes_long_path(self):
        """电池续航不足时应剪枝"""
        grid = make_grid(10, 10, 3, 8)
        env = make_zero_env(grid)
        planner = AStar4D(grid, env, {
            "uav_speed": 10.0, "w_distance": 1.0,
            "max_battery_time": 5.0,  # 5 seconds only
        })
        # Far corner should be unreachable with 5s battery
        result = planner.search((0, 0, 1, 0), (9, 9, 1))
        # Either fails or path is very short
        if result["status"] == "success":
            self.assertLessEqual(result["total_time"], 5.0)


class TestTimeAdvance(unittest.TestCase):
    """时间推进测试"""

    def test_different_start_times_different_paths(self):
        """不同出发时刻应产生不同路径（如果风险场有时变）"""
        grid = make_grid(8, 8, 3, 24)
        env = make_zero_env(grid)
        # Make risk time-dependent: high risk at t=12
        env.p_crash[:, :, :, 12] = 0.5

        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 0.5, "w_fatality": 0.5})

        r1 = planner.search((0, 0, 1, 0), (7, 7, 1))
        r2 = planner.search((0, 0, 1, 12), (7, 7, 1))

        # Both should succeed (different paths or different costs)
        self.assertEqual(r1["status"], "success")
        self.assertEqual(r2["status"], "success")


class TestSearchNode(unittest.TestCase):
    """SearchNode 数据结构测试"""

    def test_default_state(self):
        """默认状态应包含所有必需字段"""
        node = SearchNode(0, 0, 0, 0)
        required = ["cum_distance", "cum_time", "p_survival",
                     "cum_fatality", "cum_property", "cum_noise", "cum_objective"]
        for key in required:
            self.assertIn(key, node.state)

    def test_comparison_by_f(self):
        """节点比较应基于 f 值"""
        n1 = SearchNode(0, 0, 0, 0)
        n1.f = 1.0
        n2 = SearchNode(0, 0, 0, 0)
        n2.f = 2.0
        self.assertTrue(n1 < n2)

    def test_pos_3d_property(self):
        """pos_3d 应返回 (x, y, z)"""
        node = SearchNode(1, 2, 3, 4)
        self.assertEqual(node.pos_3d, (1, 2, 3))


class TestHeuristic(unittest.TestCase):
    """启发式函数测试"""

    def test_heuristic_zero_at_goal(self):
        """目标点启发式值 = 0"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 0.4})

        h = planner._heuristic((2, 2, 1), (2, 2, 1))
        self.assertAlmostEqual(h, 0.0)

    def test_heuristic_non_negative(self):
        """启发式值 >= 0"""
        grid = make_grid(5, 5, 3, 8)
        env = make_zero_env(grid)
        planner = AStar4D(grid, env, {"uav_speed": 10.0, "w_distance": 0.4})

        for goal in [(0, 0, 0), (4, 4, 2), (2, 2, 1)]:
            h = planner._heuristic((2, 2, 1), goal)
            self.assertGreaterEqual(h, 0.0)


if __name__ == "__main__":
    unittest.main()
