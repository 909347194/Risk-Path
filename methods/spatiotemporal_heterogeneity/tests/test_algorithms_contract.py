import unittest

import numpy as np

from methods.spatiotemporal_heterogeneity.src.algorithms import EnvTensor, SearchNode
from methods.spatiotemporal_heterogeneity.src.algorithms.a_star import AStar4D
from methods.spatiotemporal_heterogeneity.src.tensor_engine.grid_system import (
    GridSystem,
    SpatialGridConfig,
    TemporalGridConfig,
)


class AlgorithmsContractTest(unittest.TestCase):
    def setUp(self):
        self.grid = GridSystem(
            spatial=SpatialGridConfig(nx=5, ny=5, nz=3, dx=10.0, dy=10.0, dz=10.0),
            temporal=TemporalGridConfig(nt=8, dt_minutes=15.0),
        )

    def test_env_tensor_broadcasts_common_component_shapes(self):
        nx, ny, nz, nt = self.grid.shape
        env = EnvTensor(
            p_crash=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            fatality=np.ones((nx, ny, nt), dtype=np.float32),
            property=np.ones((nx, ny), dtype=np.float32),
            noise=np.ones((nx, ny, nz), dtype=np.float32),
            obstacle=np.zeros((nx, ny), dtype=np.float32),
            grid=self.grid,
        )

        self.assertEqual(env.shape, self.grid.shape)
        self.assertEqual(env.fatality.shape, self.grid.shape)
        self.assertEqual(env.property.shape, self.grid.shape)
        self.assertEqual(env.noise.shape, self.grid.shape)
        self.assertFalse(env.risk_at(0, 0, 0, 0)["obstacle"])

    def test_astar_respects_nonzero_start_time(self):
        nx, ny, nz, nt = self.grid.shape
        env = EnvTensor(
            p_crash=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            fatality=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            property=np.zeros((nx, ny), dtype=np.float32),
            noise=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            grid=self.grid,
        )
        planner = AStar4D(self.grid, env, {"uav_speed": 10.0, "w_distance": 1.0})
        node = SearchNode(0, 0, 1, 3, state_dict={"absolute_time": 3 * planner.time_resolution})

        expanded = planner._expand_node(node, (1, 0, 1), 10.0)

        self.assertIsNotNone(expanded)
        self.assertEqual(expanded.t, 3)
        self.assertGreater(expanded.state["absolute_time"], 3 * planner.time_resolution)

    def test_astar_finds_path_around_obstacle(self):
        nx, ny, nz, nt = self.grid.shape
        obstacle = np.zeros((nx, ny, nz, nt), dtype=np.float32)
        obstacle[2, 2, :, :] = 1.0
        env = EnvTensor(
            p_crash=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            fatality=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            property=np.zeros((nx, ny), dtype=np.float32),
            noise=np.zeros((nx, ny, nz, nt), dtype=np.float32),
            obstacle=obstacle,
            grid=self.grid,
        )
        planner = AStar4D(self.grid, env, {"uav_speed": 10.0, "w_distance": 1.0})

        result = planner.search((0, 0, 1, 0), (4, 4, 1))

        self.assertEqual(result["status"], "success")
        self.assertNotIn((2, 2, 1), [tuple(item["coords"][:3]) for item in result["path"]])


if __name__ == "__main__":
    unittest.main()
