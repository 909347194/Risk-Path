#!/usr/bin/env python3
"""实验配置加载：支持 `extends: <相对路径>` 继承公共配置（实验值覆盖公共值）。"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并：override 覆盖 base（同名键以 override 为准）。"""
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_exp_config(path: Path | None = None) -> dict:
    """读取实验配置；支持 `extends: <相对路径>` 继承公共配置。"""
    from exp_common import HERE
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
