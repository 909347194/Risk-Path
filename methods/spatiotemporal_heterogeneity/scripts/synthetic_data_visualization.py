"""
合成数据可视化脚本

对 spatiotemporal_heterogeneity 模块生成的合成城市数据进行全面可视化展示。

数据层包括：
1. 土地利用 (landuse) - 分类地图
2. 道路网络 (road_mask) - 二值掩码
3. 建筑高度 (building_heights) - 连续值表面
4. POI密度 (poi) - 多类型兴趣点
5. 人口密度 (population) - 静态密度场
6. 风场 (wind_field) - 4D时空数据
7. 降雨 (rain_data) - 3D时空数据
8. OD对 (od_pairs) - 起终点对

输出：
- Matplotlib 静态高分辨率图片（适合论文）
- Plotly 交互式HTML（适合探索）
"""

import os
import sys
import json
import numpy as np
from pathlib import Path

# 设置项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MODULE_ROOT = Path(__file__).parent.parent

# 添加模块路径
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d import Axes3D

# 设置中文字体和学术风格
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150

# Plotly 可选导入
try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    print("⚠️ plotly 未安装，将跳过交互式可视化")
    print("  安装命令: pip install plotly kaleido")


# ============================================================================
# 数据加载
# ============================================================================

def load_synthetic_data(data_dir: Path) -> dict:
    """
    加载所有合成数据文件
    
    Args:
        data_dir: 数据根目录 (methods/spatiotemporal_heterogeneity/data)
    
    Returns:
        包含所有数据的字典
    """
    processed_dir = data_dir / "02_processed" / "synthetic"
    tensors_dir = data_dir / "03_tensors" / "synthetic" / "seed_42"
    
    data = {}
    
    # 加载元数据
    metadata_path = processed_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            data['metadata'] = json.load(f)
        print(f"✅ 加载元数据: {data['metadata']['grid_dimensions']}")
    
    # 加载空间数据
    npy_files = {
        'landuse': 'landuse_map.npy',
        'road_mask': 'road_mask.npy',
        'building_heights': 'building_heights.npy',
        'population': 'base_pop_2d.npy',
    }
    
    for key, filename in npy_files.items():
        filepath = processed_dir / filename
        if filepath.exists():
            data[key] = np.load(str(filepath))
            print(f"✅ 加载 {key}: shape={data[key].shape}, dtype={data[key].dtype}")
        else:
            print(f"⚠️ 未找到 {filename}")
    
    # 加载 POI 数据 (npz 格式)
    poi_path = processed_dir / "poi_counts.npz"
    if poi_path.exists():
        poi_data = np.load(str(poi_path))
        data['poi'] = {k: poi_data[k] for k in poi_data.files}
        print(f"✅ 加载 POI: 类型={list(data['poi'].keys())}")
    
    # 加载 OD 对
    od_path = processed_dir / "od_pairs.json"
    if od_path.exists():
        with open(od_path, 'r', encoding='utf-8') as f:
            data['od_pairs'] = json.load(f)
        print(f"✅ 加载 OD对: {len(data['od_pairs'])} 对")
    
    # 加载气象张量数据
    weather_files = {
        'wind_field': 'wind_field.npy',
        'rain_data': 'rain_data.npy',
    }
    
    for key, filename in weather_files.items():
        filepath = tensors_dir / filename
        if filepath.exists():
            data[key] = np.load(str(filepath))
            print(f"✅ 加载 {key}: shape={data[key].shape}")
        else:
            print(f"⚠️ 未找到 {filename}")
    
    return data


# ============================================================================
# Matplotlib 可视化
# ============================================================================

def get_landuse_colormap():
    """获取土地利用类型的配色方案"""
    colors = ['#CCCCCC', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    labels = ['未定义', '住宅区', '商业区', '学校/医院', '工业区', '道路', '绿地/水域']
    cmap = mcolors.ListedColormap(colors)
    bounds = np.arange(-0.5, 7.5, 1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)
    return cmap, norm, labels, colors


def visualize_landuse(data: dict, output_dir: Path) -> None:
    """可视化土地利用分类图"""
    if 'landuse' not in data:
        return
    
    print("\n📊 生成土地利用可视化...")
    landuse = data['landuse']
    cmap, norm, labels, colors = get_landuse_colormap()
    
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='white')
    
    im = ax.imshow(landuse, cmap=cmap, norm=norm, origin='lower', interpolation='nearest')
    
    # 添加图例
    legend_patches = [Patch(facecolor=colors[i], edgecolor='black', label=labels[i]) 
                      for i in range(len(labels))]
    ax.legend(handles=legend_patches, loc='upper right', fontsize=9, 
              framealpha=0.9, edgecolor='black')
    
    ax.set_title('土地利用分类图 (Land Use Map)', fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('X (网格单元)', fontsize=11)
    ax.set_ylabel('Y (网格单元)', fontsize=11)
    
    # 添加统计信息
    unique, counts = np.unique(landuse, return_counts=True)
    total = landuse.size
    stats_text = "类型统计:\n"
    for u, c in zip(unique, counts):
        if u < len(labels):
            stats_text += f"  {labels[u]}: {c} ({c/total*100:.1f}%)\n"
    ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=8,
            verticalalignment='bottom', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    output_path = output_dir / '01_landuse_map.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_road_network(data: dict, output_dir: Path) -> None:
    """可视化道路网络"""
    if 'road_mask' not in data:
        return
    
    print("\n📊 生成道路网络可视化...")
    road_mask = data['road_mask']
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor='white')
    
    # 左图：道路掩码
    ax1 = axes[0]
    im1 = ax1.imshow(road_mask, cmap='binary', origin='lower', interpolation='nearest')
    ax1.set_title('道路网络掩码 (Road Mask)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('X (网格单元)')
    ax1.set_ylabel('Y (网格单元)')
    plt.colorbar(im1, ax=ax1, shrink=0.8, label='道路 (0/1)')
    
    # 右图：道路叠加在土地利用上
    ax2 = axes[1]
    if 'landuse' in data:
        landuse = data['landuse']
        cmap, norm, labels, colors = get_landuse_colormap()
        ax2.imshow(landuse, cmap=cmap, norm=norm, origin='lower', alpha=0.6)
    
    # 高亮道路
    road_overlay = np.ma.masked_where(road_mask == 0, road_mask)
    ax2.imshow(road_overlay, cmap='Reds', origin='lower', alpha=0.8, vmin=0, vmax=1)
    ax2.set_title('道路网络叠加图', fontsize=12, fontweight='bold')
    ax2.set_xlabel('X (网格单元)')
    ax2.set_ylabel('Y (网格单元)')
    
    # 统计信息
    road_ratio = np.sum(road_mask > 0) / road_mask.size * 100
    fig.suptitle(f'道路网络可视化 (覆盖率: {road_ratio:.1f}%)', 
                 fontsize=14, fontweight='bold', y=1.02)
    
    plt.tight_layout()
    output_path = output_dir / '02_road_network.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def _draw_cube(ax, x, y, z_bottom, z_top, color, alpha=0.8):
    """
    在3D坐标轴上绘制一个立方体（建筑体块）
    
    Args:
        ax: 3D坐标轴
        x, y: 底面中心坐标
        z_bottom: 底部高度
        z_top: 顶部高度
        color: 颜色
        alpha: 透明度
    """
    # 定义立方体的8个顶点
    dx, dy = 0.4, 0.4  # 半宽
    
    # 底面4个顶点
    vertices = [
        [x - dx, y - dy, z_bottom],
        [x + dx, y - dy, z_bottom],
        [x + dx, y + dy, z_bottom],
        [x - dx, y + dy, z_bottom],
        # 顶面4个顶点
        [x - dx, y - dy, z_top],
        [x + dx, y - dy, z_top],
        [x + dx, y + dy, z_top],
        [x - dx, y + dy, z_top],
    ]
    
    # 定义6个面
    faces = [
        [vertices[0], vertices[1], vertices[5], vertices[4]],  # 前面
        [vertices[2], vertices[3], vertices[7], vertices[6]],  # 后面
        [vertices[0], vertices[3], vertices[7], vertices[4]],  # 左面
        [vertices[1], vertices[2], vertices[6], vertices[5]],  # 右面
        [vertices[4], vertices[5], vertices[6], vertices[7]],  # 顶面
        [vertices[0], vertices[1], vertices[2], vertices[3]],  # 底面
    ]
    
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    
    # 绘制每个面
    for i, face in enumerate(faces):
        # 顶面颜色稍亮
        face_color = color
        if i == 4:  # 顶面
            face_color = _lighten_color(color, 0.2)
        
        poly = Poly3DCollection([face], alpha=alpha)
        poly.set_facecolor(face_color)
        poly.set_edgecolor('black')
        poly.set_linewidth(0.3)
        ax.add_collection3d(poly)


def _lighten_color(color, amount=0.3):
    """使颜色变亮"""
    import matplotlib.colors as mc
    try:
        c = mc.cnames.get(color, color)
        c = mc.to_rgb(c)
    except:
        c = color
    
    # 简单地增加亮度
    return tuple(min(1, c[i] + amount * (1 - c[i])) for i in range(3))


def get_building_height_colormap():
    """获取建筑高度的配色方案"""
    import matplotlib.cm as cm
    
    # 按高度分层配色
    height_colors = {
        'low': '#90EE90',      # 低层 (1-10层) - 浅绿
        'mid': '#FFD700',      # 中层 (10-30层) - 金黄
        'high': '#FF6347',     # 高层 (30-60层) - 番茄红
        'skyscraper': '#8B0000'  # 超高层 (>60层) - 深红
    }
    return height_colors


def get_height_color(height):
    """根据建筑高度返回颜色"""
    if height <= 10:
        return '#90EE90'  # 浅绿 - 低层
    elif height <= 30:
        return '#FFD700'  # 金黄 - 中层
    elif height <= 60:
        return '#FF6347'  # 番茄红 - 高层
    else:
        return '#8B0000'  # 深红 - 超高层


def visualize_building_heights(data: dict, output_dir: Path) -> None:
    """可视化建筑高度"""
    if 'building_heights' not in data:
        return
    
    print("\n📊 生成建筑高度可视化...")
    heights = data['building_heights']
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 6), facecolor='white')
    
    # 左图：2D 热力图
    ax1 = axes[0]
    im1 = ax1.imshow(heights, cmap='YlOrRd', origin='lower', interpolation='bilinear')
    ax1.set_title('建筑高度分布 (2D)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('X (网格单元)')
    ax1.set_ylabel('Y (网格单元)')
    plt.colorbar(im1, ax=ax1, shrink=0.8, label='高度 (层)')
    
    # 中图：3D 表面图
    ax2 = axes[1]
    step = max(1, heights.shape[0] // 30)
    Y, X = np.meshgrid(range(0, heights.shape[0], step), range(0, heights.shape[1], step))
    Z = heights[::step, ::step]
    
    ax2 = fig.add_subplot(1, 3, 2, projection='3d')
    surf = ax2.plot_surface(X, Y, Z, cmap='YlOrRd', alpha=0.8, 
                            edgecolor='black', linewidth=0.2)
    ax2.set_title('建筑高度 (3D表面)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('X')
    ax2.set_ylabel('Y')
    ax2.set_zlabel('高度 (层)')
    ax2.view_init(elev=35, azim=45)
    
    # 右图：高度直方图
    ax3 = axes[2]
    heights_flat = heights.flatten()
    heights_nonzero = heights_flat[heights_flat > 0]
    
    ax3.hist(heights_nonzero, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
    ax3.set_title('建筑高度分布 (直方图)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('高度 (层)')
    ax3.set_ylabel('频次')
    ax3.axvline(np.mean(heights_nonzero), color='red', linestyle='--', 
                label=f'均值: {np.mean(heights_nonzero):.1f}')
    ax3.legend()
    
    # 统计信息
    stats_text = (f"总网格数: {heights.size}\n"
                  f"有建筑: {np.sum(heights > 0)} ({np.sum(heights > 0)/heights.size*100:.1f}%)\n"
                  f"最大高度: {np.max(heights):.0f} 层\n"
                  f"平均高度: {np.mean(heights_nonzero):.1f} 层")
    ax3.text(0.95, 0.95, stats_text, transform=ax3.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    fig.suptitle('建筑高度可视化', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / '03_building_heights.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_building_3d_blocks(data: dict, output_dir: Path) -> None:
    """
    可视化建筑3D体块 - 真正的立方体表示每个建筑
    
    将每个有建筑的网格单元绘制成3D立方体，高度对应建筑层数。
    使用颜色编码区分不同高度等级（低层/中层/高层/超高层）。
    """
    if 'building_heights' not in data:
        return
    
    print("\n📊 生成建筑3D体块可视化...")
    heights = data['building_heights']
    landuse = data.get('landuse', None)
    
    # 创建图形 - 多视角展示
    fig = plt.figure(figsize=(20, 16), facecolor='white')
    
    # ========== 主视图：完整3D建筑体块 ==========
    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    
    # 绘制地面（半透明）
    ny, nx = heights.shape
    ground_x = [0, nx, nx, 0, 0]
    ground_y = [0, 0, ny, ny, 0]
    ground_z = [0, 0, 0, 0, 0]
    ax1.plot(ground_x, ground_y, ground_z, 'k-', linewidth=1.5, alpha=0.5)
    
    # 填充地面
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    ground_verts = [[(0, 0, 0), (nx, 0, 0), (nx, ny, 0), (0, ny, 0)]]
    ground_poly = Poly3DCollection(ground_verts, alpha=0.2)
    ground_poly.set_facecolor('#D3D3D3')  # 浅灰色地面
    ground_poly.set_edgecolor('gray')
    ax1.add_collection3d(ground_poly)
    
    # 绘制建筑体块
    building_count = 0
    for y in range(ny):
        for x in range(nx):
            h = heights[y, x]
            if h > 0.5:  # 有效建筑（至少0.5层）
                color = get_height_color(h)
                _draw_cube(ax1, x, y, 0, h, color, alpha=0.85)
                building_count += 1
    
    ax1.set_xlabel('X (网格单元)', fontsize=10, fontweight='bold')
    ax1.set_ylabel('Y (网格单元)', fontsize=10, fontweight='bold')
    ax1.set_zlabel('高度 (层)', fontsize=10, fontweight='bold')
    ax1.set_title(f'建筑3D体块 (共{building_count}栋)', fontsize=13, fontweight='bold')
    ax1.view_init(elev=35, azim=45)
    
    # 设置坐标轴范围
    ax1.set_xlim(0, nx)
    ax1.set_ylim(0, ny)
    ax1.set_zlim(0, np.max(heights) * 1.1)
    
    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#90EE90', edgecolor='black', label='低层 (1-10层)'),
        Patch(facecolor='#FFD700', edgecolor='black', label='中层 (10-30层)'),
        Patch(facecolor='#FF6347', edgecolor='black', label='高层 (30-60层)'),
        Patch(facecolor='#8B0000', edgecolor='black', label='超高层 (>60层)'),
    ]
    ax1.legend(handles=legend_elements, loc='upper left', fontsize=8, framealpha=0.9)
    
    # ========== 俯视图 ==========
    ax2 = fig.add_subplot(2, 2, 2, projection='3d')
    
    # 重绘建筑
    for y in range(ny):
        for x in range(nx):
            h = heights[y, x]
            if h > 0.5:
                color = get_height_color(h)
                _draw_cube(ax2, x, y, 0, h, color, alpha=0.85)
    
    ax2.set_xlabel('X', fontsize=9)
    ax2.set_ylabel('Y', fontsize=9)
    ax2.set_zlabel('高度', fontsize=9)
    ax2.set_title('俯视图', fontsize=12, fontweight='bold')
    ax2.view_init(elev=85, azim=0)
    ax2.set_xlim(0, nx)
    ax2.set_ylim(0, ny)
    ax2.set_zlim(0, np.max(heights) * 1.1)
    
    # ========== 侧视图 ==========
    ax3 = fig.add_subplot(2, 2, 3, projection='3d')
    
    for y in range(ny):
        for x in range(nx):
            h = heights[y, x]
            if h > 0.5:
                color = get_height_color(h)
                _draw_cube(ax3, x, y, 0, h, color, alpha=0.85)
    
    ax3.set_xlabel('X', fontsize=9)
    ax3.set_ylabel('Y', fontsize=9)
    ax3.set_zlabel('高度', fontsize=9)
    ax3.set_title('侧视图', fontsize=12, fontweight='bold')
    ax3.view_init(elev=10, azim=-90)
    ax3.set_xlim(0, nx)
    ax3.set_ylim(0, ny)
    ax3.set_zlim(0, np.max(heights) * 1.1)
    
    # ========== 前视图 ==========
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    
    for y in range(ny):
        for x in range(nx):
            h = heights[y, x]
            if h > 0.5:
                color = get_height_color(h)
                _draw_cube(ax4, x, y, 0, h, color, alpha=0.85)
    
    ax4.set_xlabel('X', fontsize=9)
    ax4.set_ylabel('Y', fontsize=9)
    ax4.set_zlabel('高度', fontsize=9)
    ax4.set_title('前视图', fontsize=12, fontweight='bold')
    ax4.view_init(elev=10, azim=0)
    ax4.set_xlim(0, nx)
    ax4.set_ylim(0, ny)
    ax4.set_zlim(0, np.max(heights) * 1.1)
    
    # 总标题
    fig.suptitle(
        f'建筑三维体块可视化\n'
        f'网格: {ny}×{nx} | 建筑数: {building_count} | '
        f'最大高度: {np.max(heights):.0f}层 | 平均高度: {np.mean(heights[heights > 0]):.1f}层',
        fontsize=14, fontweight='bold', y=0.98
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    output_path = output_dir / '03b_building_3d_blocks.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_building_3d_with_landuse(data: dict, output_dir: Path) -> None:
    """
    可视化建筑3D体块 + 土地利用底图
    
    在土地利用底图上绘制3D建筑体块，展示建筑与土地利用的关系。
    """
    if 'building_heights' not in data or 'landuse' not in data:
        return
    
    print("\n📊 生成建筑3D体块+土地利用可视化...")
    heights = data['building_heights']
    landuse = data['landuse']
    
    fig = plt.figure(figsize=(16, 12), facecolor='white')
    ax = fig.add_subplot(111, projection='3d')
    
    ny, nx = heights.shape
    
    # 先绘制土地利用底图（半透明平面）
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    
    # 土地利用颜色映射
    landuse_colors = {
        0: '#CCCCCC',  # 未定义
        1: '#FF6B6B',  # 住宅区
        2: '#4ECDC4',  # 商业区
        3: '#45B7D1',  # 学校/医院
        4: '#96CEB4',  # 工业区
        5: '#FFEAA7',  # 道路
        6: '#DDA0DD',  # 绿地/水域
    }
    
    # 绘制土地利用平面
    for y in range(ny):
        for x in range(nx):
            lu_type = landuse[y, x]
            color = landuse_colors.get(lu_type, '#CCCCCC')
            
            # 绘制地面单元格
            verts = [[(x - 0.5, y - 0.5, 0), 
                      (x + 0.5, y - 0.5, 0), 
                      (x + 0.5, y + 0.5, 0), 
                      (x - 0.5, y + 0.5, 0)]]
            
            poly = Poly3DCollection(verts, alpha=0.4)
            poly.set_facecolor(color)
            poly.set_edgecolor('none')
            ax.add_collection3d(poly)
    
    # 绘制建筑体块
    for y in range(ny):
        for x in range(nx):
            h = heights[y, x]
            if h > 0.5:
                color = get_height_color(h)
                _draw_cube(ax, x, y, 0, h, color, alpha=0.9)
    
    ax.set_xlabel('X (网格单元)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Y (网格单元)', fontsize=11, fontweight='bold')
    ax.set_zlabel('高度 (层)', fontsize=11, fontweight='bold')
    ax.set_title('建筑3D体块 + 土地利用底图', fontsize=14, fontweight='bold')
    ax.view_init(elev=35, azim=45)
    
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(-0.5, ny - 0.5)
    ax.set_zlim(0, np.max(heights) * 1.1)
    
    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#FF6B6B', edgecolor='black', alpha=0.6, label='住宅区'),
        Patch(facecolor='#4ECDC4', edgecolor='black', alpha=0.6, label='商业区'),
        Patch(facecolor='#96CEB4', edgecolor='black', alpha=0.6, label='工业区'),
        Patch(facecolor='#90EE90', edgecolor='black', label='低层建筑'),
        Patch(facecolor='#FFD700', edgecolor='black', label='中层建筑'),
        Patch(facecolor='#FF6347', edgecolor='black', label='高层建筑'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9, framealpha=0.9)
    
    plt.tight_layout()
    output_path = output_dir / '03c_building_3d_with_landuse.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_poi(data: dict, output_dir: Path) -> None:
    """可视化 POI 密度"""
    if 'poi' not in data:
        return
    
    print("\n📊 生成 POI 密度可视化...")
    poi = data['poi']
    
    n_types = len(poi)
    cols = min(4, n_types)
    rows = (n_types + cols - 1) // cols
    
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4.5 * rows), facecolor='white')
    if n_types == 1:
        axes = np.array([axes])
    axes = axes.flatten()
    
    # POI 类型配色 (5类，与 data_provision/poi_parser.py 一致)
    poi_cmaps = {
        'residential': 'Reds',
        'office': 'Blues', 
        'institution': 'Greens',
        'transport': 'Purples',
        'industrial': 'Oranges',
    }
    
    poi_labels = {
        'residential': '住宅 POI',
        'office': '办公 POI',
        'institution': '机构 POI',
        'transport': '交通 POI',
        'industrial': '工业 POI',
    }
    
    for idx, (key, arr) in enumerate(poi.items()):
        ax = axes[idx]
        cmap = poi_cmaps.get(key, 'viridis')
        
        im = ax.imshow(arr, cmap=cmap, origin='lower', interpolation='bilinear')
        label = poi_labels.get(key, key)
        ax.set_title(f'{label}密度', fontsize=11, fontweight='bold')
        ax.set_xlabel('X (网格单元)')
        ax.set_ylabel('Y (网格单元)')
        plt.colorbar(im, ax=ax, shrink=0.8, label='密度')
        
        # 添加统计
        stats = f"均值: {np.mean(arr):.2f}\n最大: {np.max(arr):.2f}"
        ax.text(0.02, 0.02, stats, transform=ax.transAxes, fontsize=8,
                verticalalignment='bottom', 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # 隐藏多余子图
    for idx in range(n_types, len(axes)):
        axes[idx].set_visible(False)
    
    fig.suptitle('POI (兴趣点) 密度分布', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / '04_poi_density.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_population(data: dict, output_dir: Path) -> None:
    """可视化人口密度"""
    if 'population' not in data:
        return
    
    print("\n📊 生成人口密度可视化...")
    population = data['population']
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 6), facecolor='white')
    
    # 左图：2D 热力图
    ax1 = axes[0]
    im1 = ax1.imshow(population, cmap='hot_r', origin='lower', interpolation='bilinear')
    ax1.set_title('人口密度分布 (2D)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('X (网格单元)')
    ax1.set_ylabel('Y (网格单元)')
    plt.colorbar(im1, ax=ax1, shrink=0.8, label='人口密度')
    
    # 中图：叠加土地利用
    ax2 = axes[1]
    if 'landuse' in data:
        landuse = data['landuse']
        cmap, norm, labels, colors = get_landuse_colormap()
        ax2.imshow(landuse, cmap=cmap, norm=norm, origin='lower', alpha=0.5)
    
    pop_overlay = np.ma.masked_where(population <= 0.01, population)
    im2 = ax2.imshow(pop_overlay, cmap='hot_r', origin='lower', alpha=0.7)
    ax2.set_title('人口密度 + 土地利用叠加', fontsize=12, fontweight='bold')
    ax2.set_xlabel('X (网格单元)')
    ax2.set_ylabel('Y (网格单元)')
    plt.colorbar(im2, ax=ax2, shrink=0.8, label='人口密度')
    
    # 右图：3D 表面
    ax3 = fig.add_subplot(1, 3, 3, projection='3d')
    step = max(1, population.shape[0] // 30)
    Y, X = np.meshgrid(range(0, population.shape[0], step), range(0, population.shape[1], step))
    Z = population[::step, ::step]
    
    surf = ax3.plot_surface(X, Y, Z, cmap='hot_r', alpha=0.8,
                            edgecolor='black', linewidth=0.2)
    ax3.set_title('人口密度 (3D)', fontsize=12, fontweight='bold')
    ax3.set_xlabel('X')
    ax3.set_ylabel('Y')
    ax3.set_zlabel('密度')
    ax3.view_init(elev=35, azim=45)
    
    fig.suptitle('人口密度可视化', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / '05_population_density.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_od_pairs(data: dict, output_dir: Path) -> None:
    """可视化 OD 对"""
    if 'od_pairs' not in data:
        return
    
    print("\n📊 生成 OD 对可视化...")
    od_pairs = data['od_pairs']
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor='white')
    
    # 左图：OD 对分布
    ax1 = axes[0]
    
    # 背景：土地利用或空白
    if 'landuse' in data:
        landuse = data['landuse']
        cmap, norm, labels, colors = get_landuse_colormap()
        ax1.imshow(landuse, cmap=cmap, norm=norm, origin='lower', alpha=0.3)
    
    # 绘制 OD 对
    origins = np.array([pair[0] for pair in od_pairs])
    destinations = np.array([pair[1] for pair in od_pairs])
    
    ax1.scatter(origins[:, 0], origins[:, 1], c='blue', s=80, marker='o', 
                label='起点 (O)', zorder=5, edgecolors='black', linewidth=1.5)
    ax1.scatter(destinations[:, 0], destinations[:, 1], c='red', s=80, marker='*', 
                label='终点 (D)', zorder=5, edgecolors='black', linewidth=1.5)
    
    # 绘制连线
    for pair in od_pairs:
        o, d = pair
        ax1.plot([o[0], d[0]], [o[1], d[1]], 'gray', alpha=0.4, linewidth=1, linestyle='--')
    
    ax1.set_title(f'OD 对分布 ({len(od_pairs)} 对)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('X (网格单元)')
    ax1.set_ylabel('Y (网格单元)')
    ax1.legend(fontsize=10)
    ax1.set_xlim(-0.5, 59.5)
    ax1.set_ylim(-0.5, 59.5)
    
    # 右图：距离分布
    ax2 = axes[1]
    distances = []
    for pair in od_pairs:
        o, d = pair
        dist = np.sqrt((o[0] - d[0])**2 + (o[1] - d[1])**2)
        distances.append(dist)
    
    ax2.hist(distances, bins=15, color='steelblue', edgecolor='black', alpha=0.7)
    ax2.axvline(np.mean(distances), color='red', linestyle='--', 
                label=f'均值: {np.mean(distances):.1f}')
    ax2.set_title('OD 对距离分布', fontsize=12, fontweight='bold')
    ax2.set_xlabel('欧氏距离 (网格单元)')
    ax2.set_ylabel('频次')
    ax2.legend()
    
    stats_text = (f"总OD对数: {len(od_pairs)}\n"
                  f"平均距离: {np.mean(distances):.1f}\n"
                  f"最大距离: {np.max(distances):.1f}\n"
                  f"最小距离: {np.min(distances):.1f}")
    ax2.text(0.95, 0.95, stats_text, transform=ax2.transAxes, fontsize=9,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))
    
    fig.suptitle('OD (起点-终点) 对可视化', fontsize=14, fontweight='bold', y=1.02)
    plt.tight_layout()
    output_path = output_dir / '06_od_pairs.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


def visualize_weather(data: dict, output_dir: Path) -> None:
    """可视化气象数据（风场和降雨）"""
    
    # 风场可视化
    if 'wind_field' in data:
        print("\n📊 生成风场可视化...")
        wind = data['wind_field']  # (ny, nx, nz, nt)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12), facecolor='white')
        
        # 选择不同时间步
        nt = wind.shape[3]
        time_steps = [0, nt // 4, nt // 2, 3 * nt // 4, nt - 1]
        time_labels = ['t=0', f't={nt//4}', f't={nt//2}', f't={3*nt//4}', f't={nt-1}']
        
        # 地面层风速 (z=0)
        for idx, (t, label) in enumerate(zip(time_steps[:5], time_labels[:5])):
            row, col = idx // 3, idx % 3
            ax = axes[row, col]
            
            # 计算风速 magnitude (取地面层 z=0)
            wind_speed = np.sqrt(wind[:, :, 0, t]**2)
            im = ax.imshow(wind_speed, cmap='coolwarm', origin='lower', interpolation='bilinear')
            ax.set_title(f'地面风速 ({label})', fontsize=11, fontweight='bold')
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            plt.colorbar(im, ax=ax, shrink=0.8, label='风速 (m/s)')
        
        # 第6个子图：风速时间变化
        ax6 = axes[1, 2]
        # 计算空间平均风速随时间变化
        avg_wind = np.mean(np.sqrt(wind[:, :, 0, :]**2), axis=(0, 1))
        ax6.plot(range(nt), avg_wind, 'b-', linewidth=2)
        ax6.set_title('平均地面风速时间序列', fontsize=11, fontweight='bold')
        ax6.set_xlabel('时间步')
        ax6.set_ylabel('平均风速 (m/s)')
        ax6.grid(True, alpha=0.3)
        
        fig.suptitle('风场时空变化可视化 (地面层)', fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        output_path = output_dir / '07_wind_field.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"  ✓ 已保存: {output_path}")
    
    # 降雨可视化
    if 'rain_data' in data:
        print("\n📊 生成降雨可视化...")
        rain = data['rain_data']  # (ny, nx, nt)
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 12), facecolor='white')
        
        nt = rain.shape[2]
        time_steps = [0, nt // 4, nt // 2, 3 * nt // 4, nt - 1]
        time_labels = ['t=0', f't={nt//4}', f't={nt//2}', f't={3*nt//4}', f't={nt-1}']
        
        for idx, (t, label) in enumerate(zip(time_steps[:5], time_labels[:5])):
            row, col = idx // 3, idx % 3
            ax = axes[row, col]
            
            im = ax.imshow(rain[:, :, t], cmap='Blues', origin='lower', interpolation='bilinear')
            ax.set_title(f'降雨强度 ({label})', fontsize=11, fontweight='bold')
            ax.set_xlabel('X')
            ax.set_ylabel('Y')
            plt.colorbar(im, ax=ax, shrink=0.8, label='降雨强度')
        
        # 第6个子图：降雨时间变化
        ax6 = axes[1, 2]
        avg_rain = np.mean(rain, axis=(0, 1))
        max_rain = np.max(rain, axis=(0, 1))
        ax6.plot(range(nt), avg_rain, 'b-', linewidth=2, label='空间平均')
        ax6.plot(range(nt), max_rain, 'r--', linewidth=1.5, label='空间最大')
        ax6.set_title('降雨强度时间序列', fontsize=11, fontweight='bold')
        ax6.set_xlabel('时间步')
        ax6.set_ylabel('降雨强度')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        
        fig.suptitle('降雨时空变化可视化', fontsize=14, fontweight='bold', y=1.02)
        plt.tight_layout()
        output_path = output_dir / '08_rain_data.png'
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        print(f"  ✓ 已保存: {output_path}")


def visualize_composite(data: dict, output_dir: Path) -> None:
    """生成综合概览图"""
    print("\n📊 生成综合概览图...")
    
    fig, axes = plt.subplots(2, 3, figsize=(20, 14), facecolor='white')
    
    # 1. 土地利用
    ax1 = axes[0, 0]
    if 'landuse' in data:
        cmap, norm, labels, colors = get_landuse_colormap()
        im1 = ax1.imshow(data['landuse'], cmap=cmap, norm=norm, origin='lower')
        legend_patches = [Patch(facecolor=colors[i], edgecolor='black', label=labels[i]) 
                          for i in range(len(labels))]
        ax1.legend(handles=legend_patches, loc='upper right', fontsize=7, framealpha=0.9)
    ax1.set_title('土地利用', fontsize=12, fontweight='bold')
    
    # 2. 道路网络
    ax2 = axes[0, 1]
    if 'road_mask' in data:
        ax2.imshow(data['road_mask'], cmap='binary', origin='lower')
    ax2.set_title('道路网络', fontsize=12, fontweight='bold')
    
    # 3. 建筑高度
    ax3 = axes[0, 2]
    if 'building_heights' in data:
        im3 = ax3.imshow(data['building_heights'], cmap='YlOrRd', origin='lower')
        plt.colorbar(im3, ax=ax3, shrink=0.8, label='层')
    ax3.set_title('建筑高度', fontsize=12, fontweight='bold')
    
    # 4. 人口密度
    ax4 = axes[1, 0]
    if 'population' in data:
        im4 = ax4.imshow(data['population'], cmap='hot_r', origin='lower')
        plt.colorbar(im4, ax=ax4, shrink=0.8)
    ax4.set_title('人口密度', fontsize=12, fontweight='bold')
    
    # 5. POI 综合
    ax5 = axes[1, 1]
    if 'poi' in data:
        poi_sum = sum(data['poi'].values())
        im5 = ax5.imshow(poi_sum, cmap='viridis', origin='lower')
        plt.colorbar(im5, ax=ax5, shrink=0.8, label='总POI密度')
    ax5.set_title('POI 综合密度', fontsize=12, fontweight='bold')
    
    # 6. OD 对
    ax6 = axes[1, 2]
    if 'od_pairs' in data:
        if 'landuse' in data:
            cmap, norm, labels, colors = get_landuse_colormap()
            ax6.imshow(data['landuse'], cmap=cmap, norm=norm, origin='lower', alpha=0.3)
        
        origins = np.array([pair[0] for pair in data['od_pairs']])
        destinations = np.array([pair[1] for pair in data['od_pairs']])
        ax6.scatter(origins[:, 0], origins[:, 1], c='blue', s=60, marker='o', 
                    label='起点', zorder=5, edgecolors='black')
        ax6.scatter(destinations[:, 0], destinations[:, 1], c='red', s=60, marker='*', 
                    label='终点', zorder=5, edgecolors='black')
        for pair in data['od_pairs']:
            ax6.plot([pair[0][0], pair[1][0]], [pair[0][1], pair[1][1]], 
                     'gray', alpha=0.3, linewidth=0.8)
        ax6.legend(fontsize=8)
    ax6.set_title('OD 对', fontsize=12, fontweight='bold')
    
    # 统一设置
    for ax in axes.flatten():
        ax.set_xlabel('X (网格单元)', fontsize=9)
        ax.set_ylabel('Y (网格单元)', fontsize=9)
    
    # 添加元数据信息
    if 'metadata' in data:
        meta = data['metadata']
        grid_dim = meta.get('grid_dimensions', {})
        info_text = (f"网格尺寸: {grid_dim.get('nx', '?')}×{grid_dim.get('ny', '?')}×"
                     f"{grid_dim.get('nz', '?')} | 时间步: {grid_dim.get('nt', '?')}\n"
                     f"随机种子: {meta.get('seed', '?')} | 生成时间: {meta.get('generated_at', '?')}")
        fig.text(0.5, 0.01, info_text, ha='center', fontsize=9, 
                 bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
    
    fig.suptitle('合成城市数据综合概览', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    output_path = output_dir / '00_composite_overview.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    print(f"  ✓ 已保存: {output_path}")


# ============================================================================
# Plotly 交互式可视化
# ============================================================================

def create_plotly_visualizations(data: dict, output_dir: Path) -> None:
    """创建 Plotly 交互式可视化"""
    if not PLOTLY_AVAILABLE:
        print("\n⚠️ 跳过 Plotly 可视化（未安装）")
        return
    
    print("\n📊 生成 Plotly 交互式可视化...")
    
    # 1. 土地利用交互图
    if 'landuse' in data:
        landuse = data['landuse']
        _, _, labels, _ = get_landuse_colormap()
        
        # 创建自定义颜色映射
        color_map = {
            0: '#CCCCCC', 1: '#FF6B6B', 2: '#4ECDC4', 
            3: '#45B7D1', 4: '#96CEB4', 5: '#FFEAA7', 6: '#DDA0DD'
        }
        
        fig = go.Figure(data=go.Heatmap(
            z=landuse,
            colorscale=[[i/6, color] for i, color in sorted(color_map.items())],
            showscale=True,
            colorbar=dict(
                title='土地类型',
                tickvals=list(range(7)),
                ticktext=labels
            ),
            hovertemplate='X: %{x}<br>Y: %{y}<br>类型: %{z}<extra></extra>'
        ))
        
        fig.update_layout(
            title='土地利用分类图 (交互式)',
            xaxis_title='X (网格单元)',
            yaxis_title='Y (网格单元)',
            width=800, height=700
        )
        
        html_path = output_dir / 'plotly_01_landuse.html'
        fig.write_html(str(html_path), include_plotlyjs='cdn')
        print(f"  ✓ 已保存 Plotly HTML: {html_path}")
    
    # 2. 建筑高度 3D 图
    if 'building_heights' in data:
        heights = data['building_heights']
        step = max(1, heights.shape[0] // 40)
        
        fig = go.Figure(data=[go.Surface(
            z=heights[::step, ::step],
            colorscale='YlOrRd',
            colorbar=dict(title='高度 (层)'),
            hovertemplate='X: %{x}<br>Y: %{y}<br>高度: %{z:.1f}层<extra></extra>'
        )])
        
        fig.update_layout(
            title='建筑高度 3D 交互图',
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='高度 (层)',
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=0.5)
            ),
            width=1000, height=800
        )
        
        html_path = output_dir / 'plotly_02_building_3d.html'
        fig.write_html(str(html_path), include_plotlyjs='cdn')
        print(f"  ✓ 已保存 Plotly HTML: {html_path}")
    
    # 3. 人口密度 3D 图
    if 'population' in data:
        pop = data['population']
        step = max(1, pop.shape[0] // 40)
        
        fig = go.Figure(data=[go.Surface(
            z=pop[::step, ::step],
            colorscale='hot_r',
            colorbar=dict(title='人口密度'),
            hovertemplate='X: %{x}<br>Y: %{y}<br>密度: %{z:.3f}<extra></extra>'
        )])
        
        fig.update_layout(
            title='人口密度 3D 交互图',
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='人口密度',
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=0.5)
            ),
            width=1000, height=800
        )
        
        html_path = output_dir / 'plotly_03_population_3d.html'
        fig.write_html(str(html_path), include_plotlyjs='cdn')
        print(f"  ✓ 已保存 Plotly HTML: {html_path}")
    
    # 4. OD 对交互图
    if 'od_pairs' in data:
        od_pairs = data['od_pairs']
        
        fig = go.Figure()
        
        # 背景热力图
        if 'landuse' in data:
            fig.add_trace(go.Heatmap(
                z=data['landuse'],
                colorscale='Greys',
                opacity=0.2,
                showscale=False
            ))
        
        # 起点
        origins = np.array([pair[0] for pair in od_pairs])
        fig.add_trace(go.Scatter(
            x=origins[:, 0], y=origins[:, 1],
            mode='markers',
            marker=dict(size=12, color='blue', symbol='circle',
                       line=dict(width=1.5, color='black')),
            name='起点 (O)',
            hovertemplate='起点<br>X: %{x}<br>Y: %{y}<extra></extra>'
        ))
        
        # 终点
        destinations = np.array([pair[1] for pair in od_pairs])
        fig.add_trace(go.Scatter(
            x=destinations[:, 0], y=destinations[:, 1],
            mode='markers',
            marker=dict(size=12, color='red', symbol='star',
                       line=dict(width=1.5, color='black')),
            name='终点 (D)',
            hovertemplate='终点<br>X: %{x}<br>Y: %{y}<extra></extra>'
        ))
        
        # 连线
        for pair in od_pairs:
            fig.add_trace(go.Scatter(
                x=[pair[0][0], pair[1][0]], y=[pair[0][1], pair[1][1]],
                mode='lines',
                line=dict(color='gray', width=1, dash='dash'),
                showlegend=False,
                hoverinfo='skip'
            ))
        
        fig.update_layout(
            title=f'OD 对交互图 ({len(od_pairs)} 对)',
            xaxis_title='X (网格单元)',
            yaxis_title='Y (网格单元)',
            width=900, height=700,
            xaxis=dict(range=[-0.5, 59.5]),
            yaxis=dict(range=[-0.5, 59.5])
        )
        
        html_path = output_dir / 'plotly_04_od_pairs.html'
        fig.write_html(str(html_path), include_plotlyjs='cdn')
        print(f"  ✓ 已保存 Plotly HTML: {html_path}")
    
    # 5. 综合仪表板
    print("\n📊 生成 Plotly 综合仪表板...")
    
    subplot_titles = ['土地利用', '建筑高度', '人口密度', 'POI综合']
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=subplot_titles,
        specs=[[{'type': 'heatmap'}, {'type': 'surface'}],
               [{'type': 'heatmap'}, {'type': 'heatmap'}]]
    )
    
    # 土地利用
    if 'landuse' in data:
        fig.add_trace(go.Heatmap(z=data['landuse'], showscale=False, colorscale='Viridis'),
                      row=1, col=1)
    
    # 建筑高度
    if 'building_heights' in data:
        step = max(1, data['building_heights'].shape[0] // 30)
        fig.add_trace(go.Surface(z=data['building_heights'][::step, ::step], showscale=False),
                      row=1, col=2)
    
    # 人口密度
    if 'population' in data:
        fig.add_trace(go.Heatmap(z=data['population'], showscale=False, colorscale='Hot'),
                      row=2, col=1)
    
    # POI
    if 'poi' in data:
        poi_sum = sum(data['poi'].values())
        fig.add_trace(go.Heatmap(z=poi_sum, showscale=False, colorscale='Viridis'),
                      row=2, col=2)
    
    fig.update_layout(
        title='合成城市数据综合仪表板',
        width=1200, height=1000,
        showlegend=False
    )
    
    html_path = output_dir / 'plotly_00_dashboard.html'
    fig.write_html(str(html_path), include_plotlyjs='cdn')
    print(f"  ✓ 已保存 Plotly 仪表板: {html_path}")
    
    # 6. 建筑3D体块交互图（Plotly Mesh3d）
    if 'building_heights' in data:
        print("\n📊 生成 Plotly 建筑3D体块交互图...")
        heights = data['building_heights']
        ny, nx = heights.shape
        
        # 收集所有建筑的顶点和面
        all_x, all_y, all_z = [], [], []
        all_i, all_j, all_k = [], [], []
        all_intensities = []
        
        vertex_offset = 0
        
        for y in range(ny):
            for x in range(nx):
                h = heights[y, x]
                if h > 0.5:
                    # 立方体的8个顶点
                    dx, dy = 0.4, 0.4
                    verts = [
                        [x - dx, y - dy, 0],    # 0: 底面
                        [x + dx, y - dy, 0],    # 1
                        [x + dx, y + dy, 0],    # 2
                        [x - dx, y + dy, 0],    # 3
                        [x - dx, y - dy, h],    # 4: 顶面
                        [x + dx, y - dy, h],    # 5
                        [x + dx, y + dy, h],    # 6
                        [x - dx, y + dy, h],    # 7
                    ]
                    
                    # 添加顶点
                    for v in verts:
                        all_x.append(v[0])
                        all_y.append(v[1])
                        all_z.append(v[2])
                        all_intensities.append(h)
                    
                    # 定义12个三角面（每个面2个三角形）
                    faces = [
                        # 底面
                        (0, 1, 2), (0, 2, 3),
                        # 顶面
                        (4, 5, 6), (4, 6, 7),
                        # 前面
                        (0, 1, 5), (0, 5, 4),
                        # 后面
                        (2, 3, 7), (2, 7, 6),
                        # 左面
                        (0, 3, 7), (0, 7, 4),
                        # 右面
                        (1, 2, 6), (1, 6, 5),
                    ]
                    
                    for face in faces:
                        all_i.append(face[0] + vertex_offset)
                        all_j.append(face[1] + vertex_offset)
                        all_k.append(face[2] + vertex_offset)
                    
                    vertex_offset += 8
        
        if all_x:
            fig = go.Figure(data=[go.Mesh3d(
                x=all_x, y=all_y, z=all_z,
                i=all_i, j=all_j, k=all_k,
                intensity=all_intensities,
                colorscale=[
                    [0, '#90EE90'],      # 低层 - 浅绿
                    [0.15, '#90EE90'],
                    [0.15, '#FFD700'],    # 中层 - 金黄
                    [0.4, '#FFD700'],
                    [0.4, '#FF6347'],     # 高层 - 番茄红
                    [0.7, '#FF6347'],
                    [0.7, '#8B0000'],     # 超高层 - 深红
                    [1.0, '#8B0000']
                ],
                opacity=0.9,
                flatshading=True,
                lighting=dict(
                    ambient=0.8,
                    diffuse=0.9,
                    specular=0.2,
                    roughness=0.5
                ),
                lightposition=dict(x=100, y=200, z=500),
                colorbar=dict(
                    title='建筑高度 (层)',
                    tickvals=[5, 20, 45, 80],
                    ticktext=['低层', '中层', '高层', '超高层']
                ),
                hovertemplate='X: %{x:.0f}<br>Y: %{y:.0f}<br>高度: %{z:.0f}层<extra></extra>'
            )])
            
            # 添加地面网格线
            for x_line in range(0, nx, 5):
                fig.add_trace(go.Scatter3d(
                    x=[x_line, x_line], y=[0, ny], z=[0, 0],
                    mode='lines',
                    line=dict(color='gray', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            for y_line in range(0, ny, 5):
                fig.add_trace(go.Scatter3d(
                    x=[0, nx], y=[y_line, y_line], z=[0, 0],
                    mode='lines',
                    line=dict(color='gray', width=1),
                    showlegend=False,
                    hoverinfo='skip'
                ))
            
            fig.update_layout(
                title={
                    'text': f'建筑3D体块交互图<br><sup>共 {vertex_offset // 8} 栋建筑</sup>',
                    'x': 0.5,
                    'font': {'size': 18}
                },
                scene=dict(
                    xaxis_title='X (网格单元)',
                    yaxis_title='Y (网格单元)',
                    zaxis_title='高度 (层)',
                    aspectmode='manual',
                    aspectratio=dict(x=1, y=1, z=0.7),
                    camera=dict(
                        eye=dict(x=1.5, y=1.5, z=1.2),
                        center=dict(x=0, y=0, z=-0.1)
                    ),
                    xaxis=dict(range=[-1, nx]),
                    yaxis=dict(range=[-1, ny]),
                    zaxis=dict(range=[0, np.max(heights) * 1.1]),
                ),
                width=1200, height=900,
                margin=dict(l=0, r=0, b=0, t=80)
            )
            
            html_path = output_dir / 'plotly_05_building_3d_blocks.html'
            fig.write_html(str(html_path), include_plotlyjs='cdn')
            print(f"  ✓ 已保存 Plotly 建筑3D体块: {html_path}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    print("=" * 60)
    print("合成数据可视化脚本")
    print("=" * 60)
    
    # 设置路径
    data_dir = MODULE_ROOT / "data"
    output_dir = MODULE_ROOT / "output" / "synthetic-data-visualization"
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n📁 数据目录: {data_dir}")
    print(f"📁 输出目录: {output_dir}")
    
    # 加载数据
    print("\n" + "-" * 40)
    print("加载合成数据...")
    print("-" * 40)
    data = load_synthetic_data(data_dir)
    
    if not data:
        print("❌ 未找到任何数据文件！")
        print("请先运行 export_synthetic_data.py 生成数据")
        return
    
    # Matplotlib 可视化
    print("\n" + "=" * 60)
    print("生成 Matplotlib 静态可视化...")
    print("=" * 60)
    
    visualize_composite(data, output_dir)
    visualize_landuse(data, output_dir)
    visualize_road_network(data, output_dir)
    visualize_building_heights(data, output_dir)
    visualize_building_3d_blocks(data, output_dir)      # 新增：建筑3D体块
    visualize_building_3d_with_landuse(data, output_dir)  # 新增：建筑+土地利用
    visualize_poi(data, output_dir)
    visualize_population(data, output_dir)
    visualize_od_pairs(data, output_dir)
    visualize_weather(data, output_dir)
    
    # Plotly 可视化
    print("\n" + "=" * 60)
    print("生成 Plotly 交互式可视化...")
    print("=" * 60)
    
    create_plotly_visualizations(data, output_dir)
    
    # 完成
    print("\n" + "=" * 60)
    print("✅ 所有可视化完成！")
    print("=" * 60)
    print(f"\n输出文件保存在: {output_dir}")
    
    # 列出生成的文件
    output_files = list(output_dir.glob('*'))
    if output_files:
        print(f"\n生成了 {len(output_files)} 个文件:")
        for f in sorted(output_files):
            size_kb = f.stat().st_size / 1024
            print(f"  📄 {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
