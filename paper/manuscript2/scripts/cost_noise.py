#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Noise spatiotemporal heterogeneity
突出：
1. 时间异质性
2. 空间-时间敏感矩阵

PDF + SVG（先注释）
"""

import numpy as np
import matplotlib.pyplot as plt

# --------------------------------
# 全局样式
# --------------------------------
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.family"] = "SimSun"  # 中文字体
plt.rcParams["font.size"] = 11
plt.rcParams["axes.linewidth"] = 0.8

# --------------------------------
# 数据
# --------------------------------
hours = np.arange(24)

# 住宅
res_curve = np.where(
    (hours >= 20) | (hours < 7),
    10.0,
    1.5
)

# 工业
ind_curve = np.where(
    (hours >= 20) | (hours < 7),
    0.5,
    1.0
)

# 商业
com_curve = np.where(
    (hours >= 20) | (hours < 7),
    1.5,
    1.0
)

# 敏感矩阵
matrix = np.array([
    [0.0, 1.0, 1.0],
    [0.2, 1.0, 0.5],
    [0.5, 1.0, 1.5],
    [0.5, 1.0, 1.5],
    [1.0, 1.5, 10.0],
    [2.0, 10.0, 10.0],
])

rows = [
    "Open space",
    "Industrial",
    "Infrastructure",
    "Commercial",
    "Residential",
    "Protected",
]

cols = [
    "Spatial\nS",
    "Day\nT",
    "Night\nT",
]

# --------------------------------
# 布局：左宽右窄
# --------------------------------
fig = plt.figure(figsize=(12, 5.5))

gs = fig.add_gridspec(
    1,
    2,
    width_ratios=[1.8, 1.0],
    wspace=0.25
)

# ==================================
# 左：时间异质性
# ==================================
ax1 = fig.add_subplot(gs[0, 0])

# 6类
open_curve = np.where(
    (hours >= 20) | (hours < 7),
    1.0,
    1.0
)

ind_curve = np.where(
    (hours >= 20) | (hours < 7),
    0.5,
    1.0
)

infra_curve = np.where(
    (hours >= 20) | (hours < 7),
    1.5,
    1.0
)

com_curve = np.where(
    (hours >= 20) | (hours < 7),
    1.5,
    1.0
)

res_curve = np.where(
    (hours >= 20) | (hours < 7),
    10.0,
    1.5
)

protected_curve = np.where(
    (hours >= 20) | (hours < 7),
    10.0,
    10.0
)

# 夜间背景
ax1.axvspan(
    20,
    24,
    alpha=0.20
)

ax1.axvspan(
    0,
    7,
    alpha=0.20
)

# 曲线
ax1.plot(
    hours,
    open_curve,
    linewidth=1.8,
    linestyle="-",
    label="开放空间"
)

ax1.plot(
    hours,
    ind_curve,
    linewidth=1.8,
    linestyle="--",
    label="工业物流"
)

ax1.plot(
    hours,
    infra_curve,
    linewidth=1.8,
    linestyle=":",
    label="基础设施"
)

ax1.plot(
    hours,
    com_curve,
    linewidth=1.8,
    linestyle="-.",
    label="商业行政"
)

ax1.plot(
    hours,
    res_curve,
    linewidth=2.3,
    label="住宅区"
)

ax1.plot(
    hours,
    protected_curve,
    linewidth=2.8,
    label="高敏感保护区"
)

# 标注
ax1.text(
    20.0,
    10.45,
    "夜间敏感增强",
    fontsize=10
)

ax1.text(
    9,
    2.0,
    "白天运行",
    fontsize=10
)

ax1.set_xlim(0, 23)
ax1.set_ylim(0, 11)

ax1.set_xticks(
    np.arange(0, 25, 4)
)

ax1.set_xlabel("24小时")
ax1.set_ylabel("惩罚系数")

ax1.set_title(
    "噪声干扰时间异质性",
    pad=10
)

# 图例分两列
ax1.legend(
    frameon=False,
    ncol=1,
    loc="center"
)
# ==================================
# 右：噪声水平与飞行高度关系
# ==================================
ax2 = fig.add_subplot(gs[0, 1])

z_vals = np.linspace(20, 200, 200)

P_ref = 1.0

distances = [0, 50, 100]

labels = [
    "水平距离 d = 0 m",
    "水平距离 d = 50 m",
    "水平距离 d = 100 m"
]

styles = [
    "-",
    "--",
    ":"
]

for d, lab, ls in zip(
    distances,
    labels,
    styles
):
    E = P_ref / (z_vals**2 + d**2)

    ax2.plot(
        z_vals,
        E,
        linewidth=2.2,
        linestyle=ls,
        label=lab
    )

ax2.annotate(
    "噪声衰减随高度增加",
    xy=(70, P_ref/(70**2)),
    xytext=(110, 0.00018),
    arrowprops=dict(
        arrowstyle="->",
        lw=0.8
    ),
    fontsize=10
)

ax2.set_xlim(20, 200)

ax2.set_xlabel("飞行高度 (m)")
ax2.set_ylabel("噪声能量暴露 (a.u.)")

ax2.set_title(
    "噪声水平与飞行高度关系",
    pad=10
)

ax2.legend(
    frameon=False,
    loc="upper right"
)

ax2.ticklabel_format(
    axis="y",
    style="sci",
    scilimits=(0, 0)
)

ax2.grid(alpha=0.2)


plt.tight_layout()

# --------------------------------
# 保存（先注释）
plt.savefig(
    "figures/noise_temporal_matrix.pdf",
    bbox_inches="tight"
)

# plt.savefig(
#     "figures/noise_temporal_matrix.svg",
#     bbox_inches="tight"
# )

plt.show()