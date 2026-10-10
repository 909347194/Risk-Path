#!/usr/bin/env python3
"""Exp2 期刊级绘图样式（Nature / IEEE 风，出版级）。

集中管理：字体、字号、配色（Okabe-Ito 色盲安全）、线型 / 标记、边框 /
刻度方向、出版分辨率。所有 figure 统一加载此处 rcParams，避免分散设置
导致的风格漂移与配色/线型私自定义。

设计取舍：
- 字体 sans-serif（Arial 优先，回退 DejaVu Sans），9 pt 基线，符合多数期刊
  "≤ 9 pt 正文、≤ 10 pt 标题" 的字号约束；
- 配色用 Okabe-Ito 色盲安全三色，专业且不刺眼，三方法在彩色 / 灰度 / 黑白
  打印下均互异（线型同时编码）；
- 去上 / 右边框、刻度朝外、细线宽，减少视觉噪音；
- savefig 300 dpi，满足出版栅格精度。
"""
from __future__ import annotations

from matplotlib import rcParams
from matplotlib.lines import Line2D

from exp_metrics import METHODS, METHOD_LABELS

# ----------------------------------------------------------------------------
# 字体 / 字号
# ----------------------------------------------------------------------------
rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "figure.titlesize": 11,
    "figure.titleweight": "bold",
    # 坐标轴线 / 刻度（细、朝外，减少噪音）
    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,
    "xtick.major.size": 3.5,
    "ytick.major.size": 3.5,
    "xtick.direction": "out",
    "ytick.direction": "out",
    # 出版分辨率
    "figure.dpi": 140,          # 屏幕预览
    "savefig.dpi": 300,         # 出版栅格
    "savefig.facecolor": "white",
    "axes.facecolor": "white",
})

# 去上 / 右边框（各 figure 仍可按需在 colorbar 等保留）
rcParams["axes.spines.top"] = False
rcParams["axes.spines.right"] = False

# ----------------------------------------------------------------------------
# 配色：Okabe-Ito 色盲安全（彩色 / 灰度 / 黑白打印三态均互异）
# ----------------------------------------------------------------------------
COLORS = {
    "distance_only": "#0072B2",   # 蓝  — Distance-only A*
    "static_risk":    "#E69F00",   # 橙  — Static-Risk A*
    "spatiotemporal": "#009E73",   # 绿  — Spatiotemporal A* (ours)
}
# 线型同时编码颜色盲 / 黑白打印场景（三方法线型互异）
LINESTYLES = {"distance_only": "--", "static_risk": ":", "spatiotemporal": "-"}
LINEWIDTHS = {"distance_only": 1.6, "static_risk": 1.8, "spatiotemporal": 2.0}
MARKERS = {"distance_only": "s", "static_risk": "^", "spatiotemporal": "o"}
MARKERSIZES = {"distance_only": 5.0, "static_risk": 5.5, "spatiotemporal": 5.5}

# ST 路径偏离 static 走廊区段的高亮色（Okabe-Ito 品红）
DEVIATION_COLOR = "#CC79A7"

# OD 起终点（清晰几何形状 + 高对比）
START_COLOR = "#2ECC71"     # 绿圆 — start
GOAL_COLOR = "#D73027"      # 红星 — goal


def line_style(method: str, label: bool = True) -> dict:
    """plot() 关键字：配色 / 线型 / 线宽（可选图例标签）。"""
    style = {"color": COLORS[method], "ls": LINESTYLES[method], "lw": LINEWIDTHS[method]}
    if label:
        style["label"] = METHOD_LABELS[method]
    return style


def marker_style(method: str, label: bool = True) -> dict:
    """plot() 关键字：配色 / 标记 / 尺寸（离散点，无连线）。"""
    style = {"color": COLORS[method], "marker": MARKERS[method],
             "ms": MARKERSIZES[method], "ls": "none",
             "markeredgecolor": "white", "markeredgewidth": 0.6}
    if label:
        style["label"] = METHOD_LABELS[method]
    return style


def method_legend_handles() -> list:
    """全局图例句柄：三种方法 + OD 起终点（单图例，避免子图重复）。"""
    handles = []
    for m in METHODS:
        handles.append(Line2D([], [], color=COLORS[m], ls=LINESTYLES[m],
                              lw=LINEWIDTHS[m], marker=MARKERS[m], ms=MARKERSIZES[m],
                              markeredgecolor="white", markeredgewidth=0.5,
                              label=METHOD_LABELS[m]))
    handles += [
        Line2D([], [], marker="o", ls="", color=START_COLOR, ms=7, mec="k", mew=0.8,
               label="start"),
        Line2D([], [], marker="*", ls="", color=GOAL_COLOR, ms=11, mec="k", mew=0.6,
               label="goal"),
    ]
    return handles


def deviation_legend_handle() -> Line2D:
    """「ST 偏离 static 走廊区段」高亮标记的图例句柄（仅在确有偏离时加入）。"""
    return Line2D([], [], marker="o", ls="", color=DEVIATION_COLOR, ms=5,
                  label="ST deviates from static (>1 cell)")


def panel_label(ax, letter: str, x: float = 0.02, y: float = 0.98) -> None:
    """子图面板字母标注（(a)/(b)/...），期刊惯例：左上角粗体。"""
    ax.text(x, y, f"({letter})", transform=ax.transAxes, fontsize=10,
            fontweight="bold", va="top", ha="left", color="black")
