#!/usr/bin/env python3
"""
实验入口模板 — 复制 _template/ 后按需改写。

要点：
1. 配置就在本目录 config.yaml，不依赖 configs/ 下的实验配置
2. load_config() 支持 extends 继承公共配置，实验值覆盖公共值
3. 产物写 output/（已 gitignore），不污染仓库

运行：python3 run.py
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
MODULE_ROOT = HERE.parents[1]                      # spatiotemporal_heterogeneity/
sys.path.insert(0, str(MODULE_ROOT / "src"))

from tensor_engine.grid_system import create_grid_from_config  # noqa: E402


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并：override 覆盖 base（同名键以 override 为准）。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(path: Path | None = None) -> dict:
    """读取实验配置；支持 `extends: <相对路径>` 继承公共配置。"""
    path = path or (HERE / "config.yaml")
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parent = cfg.pop("extends", None)
    if parent:
        parent_path = (path.parent / parent).resolve()
        if parent_path.exists():
            base = yaml.safe_load(parent_path.read_text(encoding="utf-8")) or {}
            base.pop("extends", None)
            cfg = _deep_merge(base, cfg)
        else:
            print(f"⚠ extends 指向的文件不存在，跳过继承: {parent_path}")
    return cfg


def main() -> None:
    cfg = load_config()
    exp = cfg.get("experiment", {})
    print("=" * 70)
    print(f"实验: {exp.get('name', HERE.name)}  —  {exp.get('description', '')}")
    print("=" * 70)

    # 网格：用本实验目录的配置
    grid = create_grid_from_config(HERE / "config.yaml")
    print("\n[网格]")
    print(grid.summary())

    # 自定义参数
    print("\n[实验参数]")
    for k, v in (cfg.get("params") or {}).items():
        print(f"  {k}: {v}")

    # 产物目录
    out = HERE / "output"
    out.mkdir(exist_ok=True)
    print(f"\n[产物目录] {out}")

    # TODO: 在这里写你的实验逻辑
    #   rng = np.random.default_rng(exp.get("seed", 42))
    #   ...
    #   np.save(out / "result.npy", result)

    print("\n✓ 实验流程结束")


if __name__ == "__main__":
    main()
