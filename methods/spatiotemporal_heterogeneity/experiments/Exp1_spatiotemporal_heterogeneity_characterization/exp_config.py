#!/usr/bin/env python3
"""Exp1 配置加载：支持 `extends: <相对路径>` 继承公共配置（实验值覆盖公共值）。

extends 链递归解析（如 config_rerun.yaml → config.yaml → configs/common.yaml），
带循环引用保护。此前的实现只展开一层，会把嵌套的 extends 静默丢弃。
"""
from __future__ import annotations

import copy
from pathlib import Path

import yaml


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _load_recursive(path: Path, seen: set) -> dict:
    path = path.resolve()
    if path in seen:
        raise ValueError(f"extends 循环引用: {path}")
    seen.add(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    parent = cfg.pop("extends", None)
    if parent:
        base_path = (path.parent / parent).resolve()
        if base_path.exists():
            base = _load_recursive(base_path, seen)   # 递归展开嵌套 extends
            cfg = _deep_merge(base, cfg)
        else:
            print(f"⚠ extends 指向的文件不存在，跳过继承: {base_path}")
    return cfg


def load_exp_config(path: Path) -> dict:
    """读取实验配置；支持 `extends: <相对路径>` 继承公共配置。"""
    return _load_recursive(Path(path), set())
