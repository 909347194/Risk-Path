"""
三维格网系统可视化模块

使用 Plotly 和 Matplotlib 绘制四维时空网格系统的三维可视化，
展示空间维度的格网结构（X, Y, Z），不包含时间切片。

主要功能：
1. 基于配置文件的网格系统加载
2. 交互式 3D 可视化（Plotly）
3. 静态 3D 可视化（Matplotlib）
4. 多视角展示和分层渲染
5. 高分辨率输出（适合学术论文）
"""

import numpy as np
import sys
from pathlib import Path

# 添加 src 目录到路径
src_path = Path(__file__).parent.parent
sys.path.insert(0, str(src_path))

from tensor_engine.grid_system import GridSystem, create_grid_from_config,get_macro_grid,get_micro_grid
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

try:
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("警告: plotly 未安装，将跳过交互式可视化")
from typing import Tuple, Optional
from matplotlib.colors import LinearSegmentedColormap


def visualize_grid_matplotlib(grid: GridSystem, 
                               output_dir: Path,
                               sampling_rate: int = 3) -> None:
    """
    使用 Matplotlib 绘制三维格网系统
    
    Args:
        grid: 网格系统实例
        output_dir: 输出目录路径
        sampling_rate: 采样率（降低点数以提高性能，默认3以保持清晰度）
    """
    print("正在生成 Matplotlib 3D 可视化...")
    
    # 获取坐标轴 - 降低采样率以显示更多网格细节
    x_coords = grid.x_coords[::sampling_rate]
    y_coords = grid.y_coords[::sampling_rate]
    z_heights = grid.z_heights
    
    nx_sampled = len(x_coords)
    ny_sampled = len(y_coords)
    nz = len(z_heights)
    
    # 创建图形 - 多子图布局，增大尺寸
    fig = plt.figure(figsize=(24, 20), facecolor='white')
    
    # ========== 视图1: 透视图（主视图）==========
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    _draw_grid_wireframe(ax1, x_coords, y_coords, z_heights, 
                         elev=30, azim=50, title='透视图 (Perspective View)',
                         show_scatter=True)
    
    # ========== 视图2: 俯视图 ==========
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    _draw_grid_wireframe(ax2, x_coords, y_coords, z_heights, 
                         elev=85, azim=45, title='俯视图 (Top View)',
                         show_scatter=True)
    
    # ========== 视图3: 侧视图 ==========
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    _draw_grid_wireframe(ax3, x_coords, y_coords, z_heights, 
                         elev=10, azim=-90, title='侧视图 (Side View)',
                         show_scatter=False)
    
    # ========== 视图4: 前视图 ==========
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    _draw_grid_wireframe(ax4, x_coords, y_coords, z_heights, 
                         elev=10, azim=0, title='前视图 (Front View)',
                         show_scatter=False)
    
    # 总标题
    plt.suptitle(
        f'四维时空网格系统 - 三维格网可视化\n'
        f'空间维度: {grid.spatial.nx}×{grid.spatial.ny}×{grid.spatial.nz} | '
        f'分辨率: {grid.spatial.dx:.0f}×{grid.spatial.dy:.0f}×{grid.spatial.dz:.0f}m',
        fontsize=16, fontweight='bold', y=0.995
    )
    
    plt.tight_layout()
    
    # 保存高分辨率图片
    output_path = output_dir / 'grid_3d_matplotlib.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ 已保存 Matplotlib 可视化: {output_path}")


def _draw_grid_wireframe(ax, x_coords: np.ndarray, y_coords: np.ndarray, 
                         z_heights: np.ndarray, elev: float, azim: float,
                         title: str, show_scatter: bool = True) -> None:
    """
    在 3D 坐标轴上绘制格网线框
    
    Args:
        ax: 3D 坐标轴对象
        x_coords, y_coords, z_heights: 坐标数组
        elev, azim: 视角参数
        title: 子图标题
        show_scatter: 是否显示散点标记
    """
    # 设置颜色映射 - 使用更鲜明的颜色
    colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(z_heights)))
    
    # 绘制每个高度层的水平网格线 - 增强线条可见性
    for iz, z in enumerate(z_heights):
        X, Y = np.meshgrid(x_coords, y_coords)
        Z = np.full_like(X, z)
        
        # 所有层都绘制，但调整透明度
        if iz == 0 or iz == len(z_heights) - 1:
            # 顶层和底层用较粗的线条
            ax.plot_wireframe(X, Y, Z, color=colors[iz], 
                            alpha=0.6, linewidth=1.2)
        elif iz % 2 == 0:
            # 偶数层用中等线条
            ax.plot_wireframe(X, Y, Z, color=colors[iz], 
                            alpha=0.4, linewidth=0.8)
        else:
            # 奇数层用细线条
            ax.plot_wireframe(X, Y, Z, color=colors[iz], 
                            alpha=0.25, linewidth=0.5)
    
    # 绘制垂直连接线（角点和边缘）- 加粗并提高对比度
    line_alpha = 0.8
    line_width = 2.0
    
    # 四个角的垂直线
    for x_val in [x_coords[0], x_coords[-1]]:
        for y_val in [y_coords[0], y_coords[-1]]:
            ax.plot([x_val, x_val], [y_val, y_val], 
                   [z_heights[0], z_heights[-1]], 
                   color='#E74C3C', alpha=line_alpha, linewidth=line_width)
    
    # 添加边缘垂直线（每边中间）
    mid_x = x_coords[len(x_coords)//2]
    mid_y = y_coords[len(y_coords)//2]
    
    for x_val in [mid_x]:
        for y_val in [y_coords[0], y_coords[-1]]:
            ax.plot([x_val, x_val], [y_val, y_val], 
                   [z_heights[0], z_heights[-1]], 
                   color='#E74C3C', alpha=0.6, linewidth=1.5)
    
    for x_val in [x_coords[0], x_coords[-1]]:
        for y_val in [mid_y]:
            ax.plot([x_val, x_val], [y_val, y_val], 
                   [z_heights[0], z_heights[-1]], 
                   color='#E74C3C', alpha=0.6, linewidth=1.5)
    
    # 添加散点标记 - 突出显示单元中心
    if show_scatter:
        # 采样显示散点以避免过于密集
        scatter_step = max(1, len(x_coords) // 12)
        x_scatter = x_coords[::scatter_step]
        y_scatter = y_coords[::scatter_step]
        
        # 只在顶层和底层显示散点
        for z_idx in [0, len(z_heights)-1]:
            z = z_heights[z_idx]
            X_s, Y_s = np.meshgrid(x_scatter, y_scatter)
            Z_s = np.full_like(X_s, z)
            
            marker_size = 15 if z_idx == 0 else 25
            marker_color = '#3498DB' if z_idx == 0 else '#E74C3C'
            
            ax.scatter(X_s, Y_s, Z_s, c=marker_color, s=marker_size, 
                      alpha=0.7, edgecolors='white', linewidth=0.5)
    
    # 设置标签 - 加大字体
    ax.set_xlabel('X (m)', fontsize=11, fontweight='bold', labelpad=10)
    ax.set_ylabel('Y (m)', fontsize=11, fontweight='bold', labelpad=10)
    ax.set_zlabel('Z (m)', fontsize=11, fontweight='bold', labelpad=10)
    ax.set_title(title, fontsize=13, fontweight='bold', pad=15)
    
    # 设置视角
    ax.view_init(elev=elev, azim=azim)
    
    # 设置范围 - 添加边距
    margin_x = (x_coords[-1] - x_coords[0]) * 0.05
    margin_y = (y_coords[-1] - y_coords[0]) * 0.05
    margin_z = (z_heights[-1] - z_heights[0]) * 0.05
    
    ax.set_xlim([x_coords[0] - margin_x, x_coords[-1] + margin_x])
    ax.set_ylim([y_coords[0] - margin_y, y_coords[-1] + margin_y])
    ax.set_zlim([z_heights[0] - margin_z, z_heights[-1] + margin_z])
    
    # 添加背景网格
    ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
    
    # 设置白色背景
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('w')
    ax.yaxis.pane.set_edgecolor('w')
    ax.zaxis.pane.set_edgecolor('w')


def visualize_grid_layers(grid: GridSystem, 
                          output_dir: Path,
                          num_layers: int = 6) -> None:
    """
    绘制垂直分层切片图（突出显示不同高度层）
    
    Args:
        grid: 网格系统实例
        output_dir: 输出目录路径
        num_layers: 显示的层数
    """
    print("正在生成分层切片可视化...")
    
    x_coords = grid.x_coords
    y_coords = grid.y_coords
    z_heights = grid.z_heights
    
    # 选择要显示的层 - 包含顶层和底层
    layer_indices = np.linspace(0, len(z_heights)-1, num_layers, dtype=int)
    
    fig, axes = plt.subplots(2, 3, figsize=(18, 12), 
                             subplot_kw={'projection': '3d'})
    axes = axes.flatten()
    
    # 使用更鲜明的颜色方案
    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6', '#1ABC9C']
    
    for idx, layer_idx in enumerate(layer_indices):
        if idx >= len(axes):
            break
            
        ax = axes[idx]
        z = z_heights[layer_idx]
        
        # 降低采样率以保持清晰度
        step = max(1, len(x_coords) // 20)
        X, Y = np.meshgrid(x_coords[::step], y_coords[::step])
        Z = np.full_like(X, z)
        
        # 绘制表面 - 增强边缘
        surf = ax.plot_surface(X, Y, Z, color=colors[idx % len(colors)],
                              alpha=0.6, edgecolor='black', linewidth=0.5)
        
        # 绘制加粗的边界框
        box_width = 2.5
        ax.plot([X.min(), X.max()], [Y.min(), Y.min()], [z, z], 'k-', linewidth=box_width)
        ax.plot([X.min(), X.max()], [Y.max(), Y.max()], [z, z], 'k-', linewidth=box_width)
        ax.plot([X.min(), X.min()], [Y.min(), Y.max()], [z, z], 'k-', linewidth=box_width)
        ax.plot([X.max(), X.max()], [Y.min(), Y.max()], [z, z], 'k-', linewidth=box_width)
        
        # 添加内部网格线
        grid_alpha = 0.3
        grid_width = 0.8
        for i in range(1, X.shape[0]-1, 2):
            ax.plot([X[i, 0], X[i, -1]], [Y[i, 0], Y[i, -1]], [z, z], 
                   'gray', alpha=grid_alpha, linewidth=grid_width)
        for j in range(1, X.shape[1]-1, 2):
            ax.plot([X[0, j], X[-1, j]], [Y[0, j], Y[-1, j]], [z, z], 
                   'gray', alpha=grid_alpha, linewidth=grid_width)
        
        ax.set_title(f'Z = {z:.0f}m\n(Layer {layer_idx})', 
                    fontsize=11, fontweight='bold', pad=10)
        ax.set_xlabel('X (m)', fontsize=9)
        ax.set_ylabel('Y (m)', fontsize=9)
        ax.set_zlabel('Z (m)', fontsize=9)
        ax.view_init(elev=35, azim=45)
        
        # 设置白色背景
        ax.xaxis.pane.fill = False
        ax.yaxis.pane.fill = False
        ax.zaxis.pane.fill = False
    
    # 隐藏多余的子图
    for idx in range(len(layer_indices), len(axes)):
        axes[idx].set_visible(False)
    
    plt.suptitle(f'垂直分层切片展示 ({num_layers} 个高度层)', 
                fontsize=15, fontweight='bold', y=0.98)
    plt.tight_layout()
    
    output_path = output_dir / 'grid_layers_slice.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"✓ 已保存分层切片图: {output_path}")


def visualize_grid_plotly(grid: GridSystem, 
                          output_dir: Path,
                          sampling_rate: int = 4) -> None:
    """
    使用 Plotly 绘制交互式三维格网系统
    
    Args:
        grid: 网格系统实例
        output_dir: 输出目录路径
        sampling_rate: 采样率（降低点数以提高性能，默认4保持清晰度）
    """
    if not PLOTLY_AVAILABLE:
        print("⚠ 跳过 Plotly 可视化（plotly 未安装）")
        print("  提示: uv add plotly kaleido")
        return
    
    print("正在生成 Plotly 交互式 3D 可视化...")
    
    # 获取坐标轴（降低采样率）
    x_coords = grid.x_coords[::sampling_rate]
    y_coords = grid.y_coords[::sampling_rate]
    z_heights = grid.z_heights
    
    # 创建 Plotly 图形
    fig = go.Figure()
    
    # 绘制每个高度层的网格面 - 增强可见性
    for iz, z in enumerate(z_heights):
        X, Y = np.meshgrid(x_coords, y_coords)
        Z = np.full_like(X, z)
        
        # 所有层都绘制,调整透明度
        if iz == 0 or iz == len(z_heights) - 1:
            opacity = 0.25
            line_width = 2
        elif iz % 2 == 0:
            opacity = 0.15
            line_width = 1
        else:
            opacity = 0.1
            line_width = 1  # Plotly contours width 必须是 >= 1 的整数
        
        fig.add_trace(go.Surface(
            x=X, y=Y, z=Z,
            showscale=False,
            opacity=opacity,
            colorscale=[[0, 'lightblue'], [1, 'lightblue']],
            name=f'Layer {iz}',
            hoverinfo='skip',
            contours={
                'x': {'show': True, 'color': 'black', 'width': line_width},
                'y': {'show': True, 'color': 'black', 'width': line_width}
            }
        ))
    
    # 绘制垂直边缘线（四个角 + 边缘中点）- 加粗
    edge_x = []
    edge_y = []
    edge_z = []
    
    corner_points = [
        (x_coords[0], y_coords[0]),
        (x_coords[0], y_coords[-1]),
        (x_coords[-1], y_coords[0]),
        (x_coords[-1], y_coords[-1]),
    ]
    
    for x_val, y_val in corner_points:
        edge_x.extend([x_val, x_val, None])
        edge_y.extend([y_val, y_val, None])
        edge_z.extend([z_heights[0], z_heights[-1], None])
    
    # 添加边缘中点的垂直线
    mid_x = x_coords[len(x_coords)//2]
    mid_y = y_coords[len(y_coords)//2]
    
    for x_val in [mid_x]:
        for y_val in [y_coords[0], y_coords[-1]]:
            edge_x.extend([x_val, x_val, None])
            edge_y.extend([y_val, y_val, None])
            edge_z.extend([z_heights[0], z_heights[-1], None])
    
    for x_val in [x_coords[0], x_coords[-1]]:
        for y_val in [mid_y]:
            edge_x.extend([x_val, x_val, None])
            edge_y.extend([y_val, y_val, None])
            edge_z.extend([z_heights[0], z_heights[-1], None])
    
    fig.add_trace(go.Scatter3d(
        x=edge_x, y=edge_y, z=edge_z,
        mode='lines',
        line=dict(color='#E74C3C', width=5),
        name='Vertical Edges',
        hoverinfo='skip'
    ))
    
    # 添加散点标记 - 突出单元中心
    scatter_step = max(1, len(x_coords) // 10)
    x_scatter = x_coords[::scatter_step]
    y_scatter = y_coords[::scatter_step]
    
    for z_idx, z in enumerate([z_heights[0], z_heights[-1]]):
        X_s, Y_s = np.meshgrid(x_scatter, y_scatter)
        Z_s = np.full_like(X_s, z)
        
        marker_size = 4 if z_idx == 0 else 6
        marker_color = '#3498DB' if z_idx == 0 else '#E74C3C'
        
        fig.add_trace(go.Scatter3d(
            x=X_s.flatten(), y=Y_s.flatten(), z=Z_s.flatten(),
            mode='markers',
            marker=dict(
                size=marker_size,
                color=marker_color,
                opacity=0.8,
                line=dict(color='white', width=0.5)
            ),
            name=f'Scatter Z={z:.0f}m',
            hoverinfo='skip'
        ))
    
    # 设置布局 - 优化视角
    fig.update_layout(
        title={
            'text': f'四维时空网格系统 - 交互式 3D 可视化<br>'
                    f'<sup>空间: {grid.spatial.nx}×{grid.spatial.ny}×{grid.spatial.nz} | '
                    f'分辨率: {grid.spatial.dx:.0f}×{grid.spatial.dy:.0f}×{grid.spatial.dz:.0f}m</sup>',
            'x': 0.5,
            'font': {'size': 18}
        },
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Z (m)',
            aspectmode='data',
            camera=dict(
                eye=dict(x=1.8, y=1.8, z=1.5),
                center=dict(x=0, y=0, z=0),
                up=dict(x=0, y=0, z=1)
            ),
            bgcolor='white'
        ),
        width=1400,
        height=1000,
        showlegend=False,
        margin=dict(l=0, r=0, b=0, t=100)
    )
    
    # 保存为 HTML（交互式）
    html_path = output_dir / 'grid_3d_plotly.html'
    fig.write_html(str(html_path), include_plotlyjs='cdn')
    print(f"✓ 已保存 Plotly HTML: {html_path}")
    
    # 保存为静态 PNG
    png_path = output_dir / 'grid_3d_plotly.png'
    fig.write_image(str(png_path), width=1400, height=1000, scale=2)
    print(f"✓ 已保存 Plotly PNG: {png_path}")


def generate_summary_report(grid: GridSystem, output_dir: Path) -> None:
    """
    生成网格系统摘要报告
    
    Args:
        grid: 网格系统实例
        output_dir: 输出目录路径
    """
    print("正在生成摘要报告...")
    
    report_path = output_dir / 'grid_system_summary.txt'
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("时空网格系统可视化报告\n")
        f.write("=" * 70 + "\n\n")
        
        f.write(grid.summary())
        f.write("\n\n")
        
        f.write("生成的可视化文件:\n")
        f.write("-" * 70 + "\n")
        f.write("1. grid_3d_matplotlib.png  - Matplotlib 多视角 3D 图\n")
        f.write("2. grid_3d_plotly.html     - Plotly 交互式 3D 图（推荐）\n")
        f.write("3. grid_3d_plotly.png      - Plotly 静态 3D 图\n")
        f.write("4. grid_layers_slice.png   - 垂直分层切片图\n")
        f.write("-" * 70 + "\n\n")
        
        f.write("技术细节:\n")
        f.write("-" * 70 + "\n")
        f.write(f"- 空间总单元数: {grid.spatial.total_cells:,}\n")
        f.write(f"- 时间总时长: {grid.temporal.total_hours} 小时\n")
        f.write(f"- 四维张量形状: {grid.shape}\n")
        f.write(f"- 内存占用 (float32): {grid.create_empty_tensor().nbytes / (1024**2):.2f} MB\n")
        f.write("-" * 70 + "\n")
    
    print(f"✓ 已保存: {report_path}")


def main():
    """
    主函数：执行完整的网格系统可视化流程
    """
    print("=" * 70)
    print("三维格网系统可视化")
    print("=" * 70)
    
    # 步骤1：从配置文件加载网格系统
    print("\n步骤1: 加载网格系统配置...")
    project_root = Path(__file__).parent.parent.parent
    config_path = project_root / "configs" / "micro_experiment.yaml"
    grid = get_micro_grid()
    print(grid.summary())
    
    # 步骤2：创建输出目录
    output_dir = project_root / "output" / "grid-system-pictures"
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n步骤2: 输出目录: {output_dir}")
    
    # 步骤3：生成 Matplotlib 可视化 - 降低采样率以提高清晰度
    print("\n步骤3: 生成 Matplotlib 3D 可视化...")
    visualize_grid_matplotlib(grid, output_dir, sampling_rate=3)
    
    # 步骤4：生成分层切片图 - 增加层数
    print("\n步骤4: 生成分层切片图...")
    visualize_grid_layers(grid, output_dir, num_layers=6)
    
    # 步骤5：生成 Plotly 可视化（如果安装了 kaleido）- 降低采样率
    try:
        print("\n步骤5: 生成 Plotly 交互式 3D 可视化...")
        visualize_grid_plotly(grid, output_dir, sampling_rate=4)
    except Exception as e:
        print(f"⚠ Plotly 静态导出失败（需要安装 kaleido）: {e}")
        print("  提示: pip install kaleido")
        print("  HTML 交互式版本仍可使用")
    
    # 步骤6：生成摘要报告
    print("\n步骤6: 生成摘要报告...")
    generate_summary_report(grid, output_dir)
    
    print("\n" + "=" * 70)
    print("✓ 可视化完成！所有文件已保存到:", output_dir)
    print("=" * 70)


if __name__ == "__main__":
    main()
