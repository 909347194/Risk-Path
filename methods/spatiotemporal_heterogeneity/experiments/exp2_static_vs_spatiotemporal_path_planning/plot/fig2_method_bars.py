#!/usr/bin/env python3
"""Figure 2：三方法六指标分组柱状图（逐出发时刻分组）。

覆盖 Table 1 的全部指标口径：L / R_fatal / R_property / R_noise / P_surv / T_compute
（均为真实时空场统一后评估）。

布局约定（期刊级）：去上/右边框、y 方向浅网格、全局单图例（底部）；
每面板独立标题 (a)–(f) + 量纲注记；柱顶标数值（小量级指标仅靠 y 轴无法判读
差异）；面板内统一小数位（按最大量级自适应 0–6 位，不混用科学计数法），y 轴
刻度与柱顶标签同精度；x 轴刻度仅保留底行。
"""
from __future__ import annotations

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

from exp_metrics import METHODS, METHOD_LABELS
from plot.style import COLORS, method_legend_handles, panel_label

NCOL_LEGEND = len(METHODS)


def _decimals_for(values: list) -> int:
    """面板内统一小数位：按最大量级自适应（0–6 位）。"""
    max_abs = max((abs(v) for v in values if np.isfinite(v)), default=1.0)
    if max_abs <= 0:
        return 1
    return int(np.clip(3 - np.floor(np.log10(max_abs)), 0, 6))


def plot_fig2(rows: list[dict], hours, out_path):
    # (key, panel title, ylabel)；ylabel 含量纲/属性注记
    metrics = [
        ("length_m", "(a) Path length $L$", "m"),
        ("fatal_risk", "(b) Fatal risk $R_{fatal}$", "expected fatalities"),
        ("property_risk", "(c) Property risk $R_{property}$", "expected damage (a.u.)"),
        ("noise_risk", "(d) Noise risk $R_{noise}$", "noise exposure (a.u.)"),
        ("survival", "(e) Survival $P_{surv}$", "probability (dimensionless)"),
        ("runtime_s", "(f) Planning runtime $T_{compute}$", "s"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15.0, 7.6), layout="constrained")
    fig.suptitle("Figure 2 — Method comparison at each departure time "
                 "(unified true-field evaluation)", fontsize=11, fontweight="bold")

    x = np.arange(len(hours))
    width = 0.24
    for i, (ax, (key, title, ylabel)) in enumerate(zip(axes.flat, metrics)):
        row, col = divmod(i, axes.shape[1])
        vals_all = []
        for j, method in enumerate(METHODS):
            vals = []
            for h in hours:
                row_h = next((r for r in rows if r["method"] == METHOD_LABELS[method]
                              and r["departure_hour"] == h and r.get("status") == "success"), None)
                vals.append(float(row_h[key]) if row_h else np.nan)
            vals_all.extend(vals)
            ax.bar(x + (j - 1) * width, vals, width, label=METHOD_LABELS[method],
                   color=COLORS[method], edgecolor="white", linewidth=0.6)

        # 面板内统一小数位：柱顶标签与 y 轴刻度同精度
        d = _decimals_for(vals_all)
        for j, method in enumerate(METHODS):
            pos = x + (j - 1) * width
            for xp, v in zip(pos, vals_all[j * len(hours):(j + 1) * len(hours)]):
                if np.isfinite(v):
                    ax.text(xp, v, f"{v:.{d}f}", ha="center", va="bottom",
                            fontsize=6, rotation=90, color="#333")

        ax.set_title(title, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.set_xticks(x, [f"{h:02d}:00" for h in hours])
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
        ax.yaxis.set_major_formatter(FormatStrFormatter(f"%.{d}f"))
        ax.margins(y=0.20)          # 柱顶数值标签留白，防止最高柱标签溢出面板
        if row == axes.shape[0] - 1:
            ax.set_xlabel("departure time")
        else:
            ax.tick_params(axis="x", labelbottom=False)
        panel_label(ax, chr(ord("a") + i))

    fig.legend(handles=method_legend_handles()[:NCOL_LEGEND],
               loc="outside lower center", ncol=NCOL_LEGEND, fontsize=9,
               framealpha=0.95, edgecolor="#888")

    fig.savefig(out_path, dpi=300)
    plt.close(fig)
