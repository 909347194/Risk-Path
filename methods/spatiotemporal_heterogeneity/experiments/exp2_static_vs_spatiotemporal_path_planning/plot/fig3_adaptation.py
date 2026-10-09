#!/usr/bin/env python3
"""Figure 3：适应性曲线 + 风险—长度 trade-off。

(a) 存活率随出发时刻；(b) 累计危险率随出发时刻；(c) L–H trade-off 散点
（每时刻 Static→ST 箭头：主结论 R_ST < R_static @ L_ST ≈ L_static 的直接图证）。

看点：static/distance 的路径不依赖出发时刻（fig1 可证），其指标随时刻起伏
完全是城市风险节律所致（安全裕度被危险时段吃掉）；ST 随时刻调路，曲线更优。
(c) 中箭头方向（向左/向下）即「同等或更短长度下风险更低」的 trade-off。

布局约定：全局单图例；x 轴按真实时间间距（08→12 为 4h、12→18 为 6h，
避免等距刻度误导斜率解读）；线型+标记双重编码（黑白打印可辨）。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from exp_metrics import METHODS, METHOD_LABELS
from plot.style import COLORS, LINESTYLES, MARKERS, MARKERSIZES, method_legend_handles


def _series(evaluated: dict, method: str, hours, key: str) -> list:
    return [evaluated.get(method, {}).get(h, {}).get(key, float("nan")) for h in hours]


def plot_fig3(evaluated: dict, hours, out_path):
    fig, axes = plt.subplots(1, 3, figsize=(17.5, 5.2), layout="constrained")
    fig.suptitle("Figure 3 (supporting) — Adaptation to departure time and the "
                 "risk–length trade-off (true-field evaluation)", fontsize=12.5)

    # ---------- (a) 存活率 vs 出发时刻 ----------
    ax = axes[0]
    for m in METHODS:
        ax.plot(hours, _series(evaluated, m, hours, "survival"),
                color=COLORS[m], ls=LINESTYLES[m], lw=2.0,
                marker=MARKERS[m], ms=MARKERSIZES[m], label=METHOD_LABELS[m])
    ax.set_title("(a) Survival vs departure time", fontsize=11)
    ax.set_xlabel("departure hour (h)")
    ax.set_ylabel("$P_{surv}$ (probability, dimensionless)")

    # ---------- (b) 累计危险率 vs 出发时刻 ----------
    ax = axes[1]
    for m in METHODS:
        ax.plot(hours, _series(evaluated, m, hours, "cum_hazard"),
                color=COLORS[m], ls=LINESTYLES[m], lw=2.0,
                marker=MARKERS[m], ms=MARKERSIZES[m], label=METHOD_LABELS[m])
    ax.set_title("(b) Cumulative hazard vs departure time", fontsize=11)
    ax.set_xlabel("departure hour (h)")
    ax.set_ylabel("$H=-\\sum\\ln(1-p)$ (dimensionless)")

    # x 轴按真实时间间距（08→12 是 4h，12→18 是 6h）+ 间隔标注，防斜率误读
    for ax in axes[:2]:
        ax.set_xlim(min(hours) - 1, max(hours) + 1)
        ax.set_xticks(hours, [f"{h:02d}:00" for h in hours])
        ax.grid(alpha=0.3)
        for h1, h2 in zip(hours[:-1], hours[1:]):
            ax.annotate(f"{h2 - h1}h", xy=((h1 + h2) / 2, 0),
                        xycoords=("data", "axes fraction"),
                        xytext=(0, -22), textcoords="offset points",
                        ha="center", fontsize=7.5, color="dimgray")

    # ---------- (c) L–H trade-off（主结论图证） ----------
    ax = axes[2]
    for m in METHODS:
        ax.plot(_series(evaluated, m, hours, "distance_m"),
                _series(evaluated, m, hours, "cum_hazard"),
                color=COLORS[m], marker=MARKERS[m], ms=MARKERSIZES[m] + 1.5,
                ls="none", label=METHOD_LABELS[m])
    # 每时刻 Static→ST 箭头：向左/向下 = 同等或更短长度下风险更低
    for h in hours:
        e_sta = evaluated.get("static_risk", {}).get(h, {})
        e_st = evaluated.get("spatiotemporal", {}).get(h, {})
        if e_sta.get("status") != "success" or e_st.get("status") != "success":
            continue
        ax.annotate("", xy=(e_st["distance_m"], e_st["cum_hazard"]),
                    xytext=(e_sta["distance_m"], e_sta["cum_hazard"]),
                    arrowprops=dict(arrowstyle="->,head_width=0.28,head_length=0.5",
                                    color="0.25", lw=1.8, alpha=0.9,
                                    shrinkA=6, shrinkB=6))
        ax.annotate(f"{h:02d}h", xy=(e_st["distance_m"], e_st["cum_hazard"]),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=7.5, color="dimgray")
    ax.set_title("(c) Risk–length trade-off (arrows: Static → ST)", fontsize=11)
    ax.set_xlabel("path length $L$ (m)")
    ax.set_ylabel("$H$ (dimensionless)")
    ax.grid(alpha=0.3)
    ax.text(0.03, 0.03, "← shorter & safer = better", transform=ax.transAxes,
            fontsize=8, color="dimgray")

    fig.legend(handles=method_legend_handles()[:len(METHODS)],
               loc="outside upper center", ncol=len(METHODS), fontsize=9.5)
    fig.text(0.5, 0.01,
             "note: Distance-only / Static routes are departure-time independent "
             "(see fig1); their metric variation reflects the urban risk rhythm, "
             "not route adaptation.",
             ha="center", fontsize=8.5, color="dimgray")

    fig.savefig(out_path, dpi=140)
    plt.close(fig)
