#!/usr/bin/env python3
"""Exp2 局部时间热点情景注入。

物理动机：真实风险场的时间异质性在空间上近乎相干（早高峰全城统一缩放，
R=risk(08:00)/risk(18:00) 空间 CV≈0.03），导致 ST 路径 ≈ Static 且跨出发时刻
不变，无法体现「时间感知路由」价值。

本情景在**指定网格区域、指定时段**注入一个局部高风险脉冲（高斯衰减），模拟
"时段性局部危险事件"（如临时人群聚集 / 天气单体 / 限飞时间窗）。

机制（同时产出两条关键证据）：
  - Static 用时间平均场 C̄=(1/T)Σ_t C：热点被 24 h 平均抹平为弱信号 -> 几乎不绕；
  - ST 在热点**活跃**时刻看到完整危险 -> 绕开；**冷**时段 -> 走直线。
  ⇒ (1) ST ≠ Static（路径分歧）；(2) ST 路径随出发时刻改变。两者兼得。

接入点：run.py 在 build_risk_tensors 之后、构造 EnvTensor 之前调用本函数，
由 config.yaml 的 params.localized_hazard 控制（enabled 默认开）。
"""
from __future__ import annotations

import numpy as np


def inject_localized_temporal_hazard(risk: dict, grid, cfg: dict) -> dict:
    """返回注入了局部时间热点脉冲的 risk 字典（p_crash 被原地外复制修改）。"""
    pc = np.asarray(risk["p_crash"], dtype=float).copy()
    nx, ny = grid.spatial.nx, grid.spatial.ny

    cx, cy = int(cfg["center"][0]), int(cfg["center"][1])
    r = float(cfg.get("radius", 12.0))
    h0, h1 = float(cfg["window"][0]), float(cfg["window"][1])
    mult = float(cfg.get("peak_multiplier", 8.0))
    clip = float(cfg.get("clip", 0.95))

    # 空间高斯衰减核（0..1）
    X, Y = np.meshgrid(np.arange(nx), np.arange(ny), indexing="ij")
    bump = np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2.0 * (r / 2.0) ** 2))

    # 时段掩码（小时 -> 时间片）
    hours = np.arange(grid.temporal.nt) * grid.temporal.dt_hours
    tmask = ((hours >= h0) & (hours <= h1)).astype(float)

    factor = 1.0 + (mult - 1.0) * bump[:, :, None, None] * tmask[None, None, None, :]
    pc = np.clip(pc * factor, 0.0, clip)

    risk = dict(risk)
    risk["p_crash"] = pc
    return risk


def describe(cfg: dict) -> str:
    """生成情景说明（写入运行日志 / README 辅助）。"""
    return (f"localized temporal hazard: center={tuple(cfg['center'])}, "
            f"radius={cfg.get('radius')}, window={tuple(cfg.get('window'))}h, "
            f"peak×{cfg.get('peak_multiplier')}")
