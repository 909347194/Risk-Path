#!/usr/bin/env python3
"""Figure 4：权重敏感性 —— 路径长度极差随风险规避权重的变化。"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_fig4(rows, hours, out_path):
    # 只画「全部出发时刻都成功」的行：N/A 行（部分/全部失败）无跨时刻可比性
    rows_ok = [r for r in rows if isinstance(r.get("spread_m"), (int, float))]
    rows_na = [r for r in rows if not isinstance(r.get("spread_m"), (int, float))]

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2), layout="constrained")
    if rows_na:
        fig.text(0.5, 0.005,
                 f"note: {len(rows_na)}/{len(rows)} weight setting(s) had failed "
                 "departures (spread N/A) and are omitted",
                 ha="center", fontsize=8, color="firebrick")
    if not rows_ok:
        fig.suptitle("Figure 4 — Weight sensitivity: NO comparable rows "
                     "(all departures failed)", fontsize=13)
        fig.savefig(out_path, dpi=140)
        plt.close(fig)
        return

    ratios = [r["ratio"] for r in rows_ok]
    spread = [r["spread_m"] for r in rows_ok]

    ax0 = axes[0]
    ax0.plot(ratios, spread, "o-", color="darkslateblue", lw=2)
    for x, y in zip(ratios, spread):
        ax0.annotate(f"{y:.0f}", (x, y), textcoords="offset points",
                     xytext=(0, 8), ha="center", fontsize=8)
    ax0.set_xlabel("risk aversion  $w_{fatal}/w_{ops}$")
    ax0.set_ylabel("path length spread across departure times (m)")
    ax0.set_title("(a) Path length spread vs risk aversion")
    ax0.grid(alpha=0.3)

    ax1 = axes[1]
    markers = ["o", "s", "^", "D", "v"]
    for i, r in enumerate(rows_ok):
        ax1.plot(hours, [r[f"L_{h:02d}h"] for h in hours],
                 marker=markers[i % len(markers)],
                 lw=1.8, label=f"ratio={r['ratio']:.0f} (spread {r['spread_m']:.0f} m)")
    ax1.set_xlabel("departure hour")
    ax1.set_ylabel("path length (m)")
    ax1.set_title("(b) Path length vs departure hour, per risk aversion")
    ax1.set_xticks(hours)
    ax1.legend(fontsize=8)
    ax1.grid(alpha=0.3)

    fig.suptitle("Figure 4 — Weight sensitivity: path length spread vs the "
                 "risk-aversion weight", fontsize=13)
    fig.savefig(out_path, dpi=140)
    plt.close(fig)
