#!/usr/bin/env python3
"""Exp1 公共路径引导：保证任意模块被单独 import 时也能找到 src 包。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent           # Experiment 1_.../
MODULE_ROOT = HERE.parents[1]                    # spatiotemporal_heterogeneity/
sys.path.insert(0, str(MODULE_ROOT / "src"))

RESULT_DIR = HERE / "result"
