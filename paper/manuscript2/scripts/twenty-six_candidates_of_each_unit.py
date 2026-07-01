"""
三维空间栅格化模型与 26-连通邻域可视化脚本
=========================================

展示内容：
1. 使用虚线栅格表示中心单元及其 26 个可移动方向；
2. 使用多个时间片展示栅格环境状态随时间变化。
"""

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "figures"

# 设置中文字体
rcParams["font.sans-serif"] = [
    "SimHei",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Arial Unicode MS",
]
rcParams["axes.unicode_minus"] = False
rcParams["pdf.fonttype"] = 42
rcParams["ps.fonttype"] = 42


# ==================== 辅助函数 ====================
def cube_vertices(position, size=1.0):
    """返回立方体的 8 个顶点。"""
    x, y, z = position
    return np.array(
        [
            [x, y, z],
            [x + size, y, z],
            [x + size, y + size, z],
            [x, y + size, z],
            [x, y, z + size],
            [x + size, y, z + size],
            [x + size, y + size, z + size],
            [x, y + size, z + size],
        ]
    )


def draw_voxel(
    ax,
    position,
    size=1.0,
    color="lightblue",
    alpha=0.6,
    edge_color="black",
    wireframe=True,
    linewidth=1.0,
    linestyle="--",
):
    """在 3D 坐标中绘制单个立方体体素。"""
    vertices = cube_vertices(position, size)

    if wireframe:
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),
        ]

        for start, end in edges:
            edge = vertices[[start, end]]
            ax.plot(
                edge[:, 0],
                edge[:, 1],
                edge[:, 2],
                color=edge_color,
                alpha=alpha,
                linewidth=linewidth,
                linestyle=linestyle,
            )
        return

    faces = [
        [vertices[i] for i in [0, 1, 2, 3]],
        [vertices[i] for i in [4, 5, 6, 7]],
        [vertices[i] for i in [0, 1, 5, 4]],
        [vertices[i] for i in [2, 3, 7, 6]],
        [vertices[i] for i in [0, 3, 7, 4]],
        [vertices[i] for i in [1, 2, 6, 5]],
    ]

    poly3d = Poly3DCollection(
        faces,
        alpha=alpha,
        facecolor=color,
        edgecolor=edge_color,
        linewidth=linewidth,
    )
    ax.add_collection3d(poly3d)


def draw_lattice(
    ax,
    origin,
    shape,
    color="#7A8794",
    alpha=0.55,
    linewidth=0.85,
    linestyle=(0, (3, 3)),
):
    """绘制三维虚线栅格，避免重复绘制体素边导致重影。"""
    x0, y0, z0 = origin
    nx, ny, nz = shape
    xs = np.arange(x0, x0 + nx + 1)
    ys = np.arange(y0, y0 + ny + 1)
    zs = np.arange(z0, z0 + nz + 1)

    for y in ys:
        for z in zs:
            ax.plot([xs[0], xs[-1]], [y, y], [z, z], color=color, alpha=alpha, linewidth=linewidth, linestyle=linestyle)
    for x in xs:
        for z in zs:
            ax.plot([x, x], [ys[0], ys[-1]], [z, z], color=color, alpha=alpha, linewidth=linewidth, linestyle=linestyle)
    for x in xs:
        for y in ys:
            ax.plot([x, x], [y, y], [zs[0], zs[-1]], color=color, alpha=alpha, linewidth=linewidth, linestyle=linestyle)


def set_voxel_axes(ax, origin, shape, elev=24, azim=-50):
    """统一体素图的比例、视角和边界。"""
    x0, y0, z0 = origin
    nx, ny, nz = shape
    pad = 0.1
    ax.set_xlim(x0 - pad, x0 + nx + pad)
    ax.set_ylim(y0 - pad, y0 + ny + pad)
    ax.set_zlim(z0 - pad, z0 + nz + pad)
    ax.set_box_aspect((nx, ny, nz))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


def save_figure(fig, filename):
    """保存为论文推荐的 PDF 矢量图。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / filename
    fig.savefig(output_path, format="pdf", bbox_inches="tight")
    print(f"已保存矢量图: {output_path.relative_to(PROJECT_ROOT)}")


def generate_neighbor_offsets():
    """生成 26 个相邻体素方向。"""
    offsets = []
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            for dz in [-1, 0, 1]:
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                offsets.append((dx, dy, dz))
    return np.array(offsets)


# ==================== 第一部分：26-连通邻域可视化 ====================
def plot_26_neighbors(show=True):
    """绘制中心单元及其 26 个可移动方向。"""
    fig = plt.figure(figsize=(5.8, 4.6))
    ax = fig.add_subplot(111, projection="3d")

    grid_origin = (-1, -1, -1)
    grid_shape = (3, 3, 3)
    center_voxel = np.array([0, 0, 0])
    center_point = center_voxel + 0.5

    draw_lattice(ax, grid_origin, grid_shape, color="#7B8794", alpha=0.62, linewidth=0.9)
    draw_voxel(
        ax,
        center_voxel,
        color="#E74C3C",
        alpha=0.26,
        edge_color="#C0392B",
        wireframe=False,
        linewidth=0.6,
    )

    offsets = generate_neighbor_offsets()
    styles = {
        1: {"label": "轴向方向 6", "color": "#2F80ED", "linewidth": 1.8, "alpha": 0.95},
        2: {"label": "边对角方向 12", "color": "#00A6A6", "linewidth": 1.35, "alpha": 0.82},
        3: {"label": "体对角方向 8", "color": "#F2994A", "linewidth": 1.1, "alpha": 0.78},
    }

    for active_axes, style in styles.items():
        vectors = np.array([offset for offset in offsets if np.count_nonzero(offset) == active_axes])
        starts = np.repeat(center_point.reshape(1, 3), len(vectors), axis=0)
        endpoints = starts + vectors

        # 使用直线连接中心点到各个方向终点
        for i in range(len(starts)):
            ax.plot(
                [starts[i, 0], endpoints[i, 0]],
                [starts[i, 1], endpoints[i, 1]],
                [starts[i, 2], endpoints[i, 2]],
                color=style["color"],
                linewidth=style["linewidth"],
                alpha=style["alpha"],
            )
        
        ax.scatter(
            endpoints[:, 0],
            endpoints[:, 1],
            endpoints[:, 2],
            c=style["color"],
            s=32,
            alpha=0.9,
            depthshade=False,
        )

    ax.scatter(
        center_point[0],
        center_point[1],
        center_point[2],
        c="#C0392B",
        s=80,
        edgecolors="#7B241C",
        linewidths=0.8,
        depthshade=False,
        zorder=20,
    )

    handles = [
        Line2D([0], [0], color=style["color"], marker="o", linewidth=style["linewidth"], markersize=5, label=style["label"])
        for style in styles.values()
    ]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=3, frameon=False, fontsize=10)

    set_voxel_axes(ax, grid_origin, grid_shape, elev=24, azim=-48)

    # 调整布局以适应图例和图形
    fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.12)

    # 保存为PDF矢量图
    save_figure(
        fig, 
        "figure1_26_neighbors.pdf",
    )

    if show:
        plt.show()
    return fig


# ==================== 第二部分：时空环境演化 ====================
STATE_STYLES = {
    "low": {"label": "低风险", "color": "#59C3A6", "alpha": 0.20},
    "mid": {"label": "中风险", "color": "#F2C94C", "alpha": 0.42},
    "high": {"label": "高风险", "color": "#EB5757", "alpha": 0.62},
    "blocked": {"label": "动态禁行", "color": "#4D5566", "alpha": 0.68},
}


def frame_layers():
    """三帧固定状态，用于明确表达同一空间栅格在不同时刻的差异。"""
    return [
        {
            "title": r"$\mathcal{G}(t_1)$",
            "layers": [
                [
                    ["low", "low", "mid", "high"],
                    ["low", "mid", "mid", "high"],
                    ["low", "low", "mid", "blocked"],
                    ["low", "low", "low", "mid"],
                ],
                [
                    ["low", "low", "low", "mid"],
                    ["low", "low", "mid", "high"],
                    ["low", "low", "mid", "blocked"],
                    ["low", "low", "low", "low"],
                ],
            ],
        },
        {
            "title": r"$\mathcal{G}(t_2)$",
            "layers": [
                [
                    ["low", "mid", "high", "high"],
                    ["low", "mid", "blocked", "high"],
                    ["low", "mid", "mid", "mid"],
                    ["low", "low", "mid", "low"],
                ],
                [
                    ["low", "mid", "mid", "high"],
                    ["low", "low", "blocked", "high"],
                    ["low", "mid", "mid", "mid"],
                    ["low", "low", "low", "low"],
                ],
            ],
        },
        {
            "title": r"$\mathcal{G}(t_k)$",
            "layers": [
                [
                    ["mid", "high", "high", "mid"],
                    ["mid", "blocked", "high", "mid"],
                    ["low", "mid", "blocked", "low"],
                    ["low", "low", "mid", "low"],
                ],
                [
                    ["mid", "high", "mid", "low"],
                    ["low", "blocked", "high", "mid"],
                    ["low", "mid", "blocked", "low"],
                    ["low", "low", "low", "low"],
                ],
            ],
        },
    ]


def draw_time_grid(ax, frame, grid_shape):
    """绘制一个时间片的三维栅格状态。"""
    draw_lattice(ax, (0, 0, 0), grid_shape, color="#8391A1", alpha=0.48, linewidth=0.75)

    cell_gap = 0.05
    cell_size = 1.0 - 2 * cell_gap
    layers = frame["layers"]
    for z, layer in enumerate(layers):
        for y, row in enumerate(layer):
            for x, state in enumerate(row):
                style = STATE_STYLES[state]
                draw_voxel(
                    ax,
                    (x + cell_gap, y + cell_gap, z + cell_gap),
                    size=cell_size,
                    color=style["color"],
                    alpha=style["alpha"],
                    edge_color=style["color"],
                    wireframe=False,
                    linewidth=0.3,
                )

    set_voxel_axes(ax, (0, 0, 0), grid_shape, elev=22, azim=-50)
    ax.set_title(frame["title"], fontsize=13, fontweight="bold", y=0.95)


def plot_spacetime_evolution(show=True):
    """绘制多个空间网格时间片，展示栅格状态随时间变化。"""
    fig = plt.figure(figsize=(13.5, 5.8))
    gs = fig.add_gridspec(
        2,
        5,
        height_ratios=[5.0, 0.85],
        width_ratios=[1.0, 0.12, 1.0, 0.16, 1.0],
        hspace=0.02,
        wspace=0.02,
    )

    frames = frame_layers()
    grid_shape = (4, 4, 2)
    panel_columns = [0, 2, 4]
    for column, frame in zip(panel_columns, frames):
        ax = fig.add_subplot(gs[0, column], projection="3d")
        draw_time_grid(ax, frame, grid_shape)

    for column, text in [(1, r"$\rightarrow$"), (3, r"$\cdots$")]:
        ax_symbol = fig.add_subplot(gs[0, column])
        ax_symbol.set_axis_off()
        ax_symbol.text(0.5, 0.55, text, fontsize=24, ha="center", va="center", color="#4D5566")

    ax_timeline = fig.add_subplot(gs[1, :])
    ax_timeline.set_xlim(0, 1)
    ax_timeline.set_ylim(0, 1)
    ax_timeline.set_axis_off()
    ax_timeline.annotate(
        "",
        xy=(0.92, 0.55),
        xytext=(0.08, 0.55),
        arrowprops=dict(arrowstyle="->", lw=2.2, color="#333333"),
    )
    time_positions = [0.18, 0.50, 0.82]
    time_labels = [r"$t_1$", r"$t_2$", r"$t_k$"]
    for pos, label in zip(time_positions, time_labels):
        ax_timeline.plot(pos, 0.55, "o", color="#333333", markersize=5)
        ax_timeline.text(pos, 0.24, label, fontsize=11, ha="center", fontweight="bold")
    ax_timeline.text(0.05, 0.24, "0", fontsize=10, ha="center")
    ax_timeline.text(0.94, 0.24, "T", fontsize=10, ha="center")

    legend_handles = [
        mpatches.Patch(color=style["color"], alpha=style["alpha"], label=style["label"])
        for style in STATE_STYLES.values()
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        fontsize=10,
        bbox_to_anchor=(0.5, 0.015),
    )
    fig.suptitle(r"时变三维栅格环境 $\mathcal{G}(t)$", fontsize=15, fontweight="bold", y=0.96)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.90, bottom=0.16)

    save_figure(
        fig, 
        filename="spacetime_grid_evolution.pdf",
    )
    if show:
        plt.show()
    return fig


# ==================== 主程序 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("三维空间栅格化模型可视化")
    print("=" * 60)

    print("\n[1/2] 绘制虚线栅格与 26 个可移动方向...")
    plot_26_neighbors()

    print("\n[2/2] 绘制随时间变化的三维栅格...")
    plot_spacetime_evolution()

    print("\n" + "=" * 60)
    print("所有图形已生成")
    print("=" * 60)
