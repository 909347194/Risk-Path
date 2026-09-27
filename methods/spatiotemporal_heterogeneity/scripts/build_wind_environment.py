"""
构建并保存情景化低空风环境 4D 张量。

入口（data_provision 仅负责加载，此处由 tensor_engine 负责生成，高度维 nz 只在
本层扩展）：

    python -m methods.spatiotemporal_heterogeneity.scripts.build_wind_environment \
        --mode micro --data-type synthetic --scenario moderate

产出：
    data/03_tensors/{data_type}/wind_speed_4d.npy           (nx, ny, nz, nt) float32, m/s
    data/03_tensors/{data_type}/wind_environment_metadata.json

说明：本脚本不下载/不依赖 ERA5；风场为情景化合成，metadata.is_observed=False。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 让脚本可独立运行：把 src/ 加入路径，使 `tensor_engine` / `data_provision` 可导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np

from tensor_engine.grid_system import GridSystem, get_micro_grid, get_macro_grid
from tensor_engine.wind_environment import ScenarioWindEnvironment
from tensor_engine.config_manager import load_config
from data_provision.paths import get_data_paths
from data_provision.pipeline import DataPipeline


def _build_grid(mode: str) -> GridSystem:
    return get_micro_grid() if mode == "micro" else get_macro_grid()


def main():
    parser = argparse.ArgumentParser(description="Build scenario-based low-altitude wind tensor")
    parser.add_argument("--mode", choices=["micro", "macro"], default="micro")
    parser.add_argument("--data-type", default="synthetic",
                        help="落盘子目录（与 paths 的 data_type 对应）")
    parser.add_argument("--scenario", default=None,
                        help="风情景 weak/moderate/strong；缺省用配置 default_scenario")
    parser.add_argument("--config", default=None, help="common.yaml 路径（可选）")
    args = parser.parse_args()

    config = load_config()  # common.yaml（项目仅有此配置；实验配置按需扩展）
    wind_cfg = config.wind_environment
    grid = _build_grid(args.mode)

    # 建筑高度（城市形态输入）：优先 pipeline 解析，缺失则提示
    paths = get_data_paths(args.data_type)
    if paths.building_heights_path.exists():
        building = np.load(paths.building_heights_path).astype(np.float32)
    else:
        print(f"[warn] 未找到建筑高度 {paths.building_heights_path}；"
              f"用零高度（全开敞，F_urban≈1）构建。")
        building = np.zeros((grid.spatial.nx, grid.spatial.ny), dtype=np.float32)

    wind_env = ScenarioWindEnvironment(
        config=wind_cfg, scenario_name=args.scenario,
    )
    wind_4d = wind_env.build_wind_tensor(grid=grid, building_heights=building)
    # paths.tensors 已含 data_type（如 03_tensors/synthetic）；data_type=None 直接落盘到该目录
    saved = wind_env.save(paths.tensors, data_type=None)

    print(f"[ok] 风场形状 {wind_4d.shape} | 范围 "
          f"{float(wind_4d.min()):.3f}–{float(wind_4d.max()):.3f} m/s")
    print(f"[ok] 保存: {saved['wind_path']}")
    print(f"[ok] 元数据: {saved['meta_path']} (is_observed="
          f"{wind_env.get_metadata()['is_observed']})")


if __name__ == "__main__":
    main()
