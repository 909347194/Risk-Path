#!/usr/bin/env python3
"""Figure 3：适应性曲线 + 风险—长度 trade-off。

(a) 存活率随出发时刻；(b) 累计危险率随出发时刻；(c) L–H trade-off 散点
（每时刻 Static→ST 箭头：主结论 R_ST < R_static @ L_ST ≈ L_static 的直接图证）。

看点：static / distance 的路径不依赖出发时刻（fig1 可证），其指标随时刻起伏
完全是城市风险节律所致（安全裕度被危险时段吃掉）；ST 随时刻调路，曲线更优。
(c) 中箭头方向（向左/向下）即「同等或更短长度下风险更低」的 trade-off。

布局约定（期刊级）：去上/右边框、浅网格、全局单图例（底部，判读注释挂为
图例标题）；x 轴按真实时间间距（08→12 为 4 h、12→18 为 6 h，
避免等距刻度误导斜率解读）；线型 + 标记双重编码（黑白打印可辨）；
散点带白边、留边距防裁剪。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_metrics import METHODS, METHOD_LABELS
from plot.style import (COLORS, LINESTYLES, MARKERS, MARKERSIZES,
                        method_legend_handles, panel_label)

NCOL_LEGEND = len(METHODS)


def _series(evaluated: dict, method: str, hours, key: str) -> list:
    return [evaluated.get(method, {}).get(h, {}).get(key, float("nan")) for h in hours]


def plot_fig3(evaluated: dict, hours, out_path):
    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8), layout="constrained")
    fig.suptitle("Figure 3 — Adaptation to departure time and the "
                 "risk–length trade-off (true-field evaluation)",
                 fontsize=11, fontweight="bold")

    # ---------- (a) 存活率 vs 出发时刻 ----------
    ax = axes[0]
    for m in METHODS:
        ax.plot(hours, _series(evaluated, m, hours, "survival"),
                color=COLORS[m], ls=LINESTYLES[m], lw=2.0,
                marker=MARKERS[m], ms=MARKERSIZES[m] + 1.0,
                markeredgecolor="white", markeredgewidth=0.6,
                label=METHOD_LABELS[m])
    ax.set_title("(a) Survival vs departure time", fontsize=10)
    ax.set_xlabel("departure hour (h)")
    ax.set_ylabel("$P_{surv}$ (probability, dimensionless)")

    # ---------- (b) 累计危险率 vs 出发时刻 ----------
    ax = axes[1]
    for m in METHODS:
        ax.plot(hours, _series(evaluated, m, hours, "cum_hazard"),
                color=COLORS[m], ls=LINESTYLES[m], lw=2.0,
                marker=MARKERS[m], ms=MARKERSIZES[m] + 1.0,
                markeredgecolor="white", markeredgewidth=0.6,
                label=METHOD_LABELS[m])
    ax.set_title("(b) Cumulative hazard vs departure time", fontsize=10)
    ax.set_xlabel("departure hour (h)")
    ax.set_ylabel("$H=-\\sum\\ln(1-p)$ (dimensionless)")

    # x 轴按真实时间间距（08→12 是 4 h，12→18 是 6 h）+ 间隔标注，防斜率误读
    for ax in axes[:2]:
        ax.set_xlim(min(hours) - 1, max(hours) + 1)
        ax.set_xticks(hours, [f"{h:02d}:00" for h in hours])
        ax.grid(alpha=0.25)
        ax.set_axisbelow(True)
        for h1, h2 in zip(hours[:-1], hours[1:]):
            ax.annotate(f"{h2 - h1} h", xy=((h1 + h2) / 2, 0),
                        xycoords=("data", "axes fraction"),
                        xytext=(0, -22), textcoords="offset points",
                        ha="center", fontsize=7.5, color="dimgray")

    # ---------- (c) L–H trade-off（主结论图证） ----------
    ax = axes[2]
    for m in METHODS:
        ax.scatter(_series(evaluated, m, hours, "distance_m"),
                   _series(evaluated, m, hours, "cum_hazard"),
                   color=COLORS[m], marker=MARKERS[m], s=(MARKERSIZES[m] + 1.5) ** 2,
                   edgecolors="white", linewidths=0.7,
                   zorder=3, label=METHOD_LABELS[m])
    # 每时刻 Static→ST 箭头：向左/向下 = 同等或更短长度下风险更低
    for h in hours:
        e_sta = evaluated.get("static_risk", {}).get(h, {})
        e_st = evaluated.get("spatiotemporal", {}).get(h, {})
        if e_sta.get("status") != "success" or e_st.get("status") != "success":
            continue
        ax.annotate("", xy=(e_st["distance_m"], e_st["cum_hazard"]),
                    xytext=(e_sta["distance_m"], e_sta["cum_hazard"]),
                    arrowprops=dict(arrowstyle="->,head_width=0.25,head_length=0.45",
                                    color="#333", lw=1.5, alpha=0.9,
                                    shrinkA=6, shrinkB=6))
        ax.annotate(f"{h:02d}h", xy=(e_st["distance_m"], e_st["cum_hazard"]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=7.5, color="dimgray")
    ax.set_title("(c) Risk–length trade-off (arrows: Static → ST)", fontsize=10)
    ax.set_xlabel("path length $L$ (m)")
    ax.set_ylabel("$H$ (dimensionless)")
    ax.grid(alpha=0.25)
    ax.set_axisbelow(True)
    ax.margins(x=0.08, y=0.10)     # 散点贴边会被裁剪，留出边距
    ax.text(0.03, 0.03, "← shorter & safer = better", transform=ax.transAxes,
            fontsize=8, color="dimgray")

    # 全局单图例放底部；判读注释挂为图例标题（fig.text 不受 layout 管理，会压 x 轴）
    fig.legend(handles=method_legend_handles()[:NCOL_LEGEND],
               loc="outside lower center", ncol=NCOL_LEGEND, fontsize=9,
               framealpha=0.95, edgecolor="#888",
               title="note: Distance-only / Static routes are departure-time independent "
                     "(see fig1); their metric variation reflects the urban risk rhythm, "
                     "not route adaptation.",
               title_fontsize=8.5)
    for i, ax in enumerate(axes):
        panel_label(ax, chr(ord("a") + i))

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
