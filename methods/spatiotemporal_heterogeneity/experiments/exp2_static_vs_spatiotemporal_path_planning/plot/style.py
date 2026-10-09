#!/usr/bin/env python3
"""Exp2 共享绘图样式：三种方法的配色/线型/标记在所有 figure 中保持一致。

集中管理以避免各 figure 私自定义导致的漂移（颜色、线型、图例标签同源）。
"""
from __future__ import annotations

from matplotlib.lines import Line2D

from exp_metrics import METHODS, METHOD_LABELS

COLORS = {
    "distance_only": "tab:blue",
    "static_risk": "tab:orange",
    "spatiotemporal": "tab:green",
}
# 线型同时编码颜色盲/黑白打印场景（三方法线型互异）
LINESTYLES = {"distance_only": "--", "static_risk": ":", "spatiotemporal": "-"}
LINEWIDTHS = {"distance_only": 1.8, "static_risk": 2.2, "spatiotemporal": 2.4}
MARKERS = {"distance_only": "s", "static_risk": "^", "spatiotemporal": "o"}
MARKERSIZES = {"distance_only": 6.5, "static_risk": 7.0, "spatiotemporal": 7.5}

# ST 路径偏离 static 走廊区段的高亮色
DEVIATION_COLOR = "magenta"


def line_style(method: str, label: bool = True) -> dict:
    """plot() 关键字：配色/线型/线宽（可选图例标签）。"""
    style = {"color": COLORS[method], "ls": LINESTYLES[method], "lw": LINEWIDTHS[method]}
    if label:
        style["label"] = METHOD_LABELS[method]
    return style


def marker_style(method: str, label: bool = True) -> dict:
    """plot() 关键字：配色/标记/尺寸（离散点，无连线）。"""
    style = {"color": COLORS[method], "marker": MARKERS[method],
             "ms": MARKERSIZES[method], "ls": "none"}
    if label:
        style["label"] = METHOD_LABELS[method]
    return style


def method_legend_handles() -> list:
    """全局图例句柄：三种方法 + OD 起终点（单图例，避免子图重复）。"""
    handles = []
    for m in METHODS:
        handles.append(Line2D([], [], color=COLORS[m], ls=LINESTYLES[m],
                              lw=LINEWIDTHS[m], marker=MARKERS[m], ms=MARKERSIZES[m],
                              label=METHOD_LABELS[m]))
    handles += [
        Line2D([], [], marker="o", ls="", color="lime", ms=9, mec="k", mew=1.2,
               label="start"),
        Line2D([], [], marker="*", ls="", color="red", ms=14, label="goal"),
    ]
    return handles


def deviation_legend_handle() -> Line2D:
    """「ST 偏离 static 走廊区段」高亮标记的图例句柄（仅在确有偏离时加入）。"""
    return Line2D([], [], marker="o", ls="", color=DEVIATION_COLOR, ms=5,
                  label="ST deviates from static (>1 cell)")
