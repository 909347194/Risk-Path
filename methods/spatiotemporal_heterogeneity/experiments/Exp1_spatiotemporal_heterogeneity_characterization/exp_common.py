#!/usr/bin/env python3
"""Exp1 公共路径引导：保证任意模块被单独 import 时也能找到 src 包。"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent           # Exp1_.../
MODULE_ROOT = HERE.parents[1]                    # spatiotemporal_heterogeneity/
sys.path.insert(0, str(MODULE_ROOT / "src"))

RESULT_DIR = HERE / "results"


def fmt_hour(h) -> str:
    """小时（可为小数，如 5.75）→ 显示标签 'HH:MM'（5.75 → '05:45'）。"""
    total = int(round(float(h) * 60))
    return f"{total // 60:02d}:{total % 60:02d}"


def hour_tag(h) -> str:
    """小时 → CSV 列名短标签：整点 8 → '08'；小数 5.75 → '0545'。

    与 fmt_hour 分工：fmt_hour 给图/日志用，hour_tag 给 CSV 列名用
    （整点保持旧列名 L_08h 兼容）。
    """
    total = int(round(float(h) * 60))
    hh, mm = divmod(total, 60)
    return f"{hh:02d}" if mm == 0 else f"{hh:02d}{mm:02d}"
