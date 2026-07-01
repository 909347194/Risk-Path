"""
城市建筑因子 f_obs 可视化脚本
==============================
可视化不同城市场景的建筑复杂度指标 R_canyon

公式：
R_canyon(x,y,z) = w_1 [1 - SVF(x,y,z)]^α + w_2 H_avg/(z + ε) + w_3 D_building

场景包括：
- 开阔地 (R_canyon = 0)
- 低密度区 (R_canyon = 0.2)
- 中密度区 (R_canyon = 0.5)
- 高密度区 (R_canyon = 0.8)
- 城市峡谷 (R_canyon = 1.0)
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# 设置中文字体（Windows系统）
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False


def draw_building(ax, x, y, height, width=0.8, color='#7B8794', alpha=0.7):
    """绘制单个建筑物（立方体）"""
    vertices = np.array([
        [x-width/2, y-width/2, 0],
        [x+width/2, y-width/2, 0],
        [x+width/2, y+width/2, 0],
        [x-width/2, y+width/2, 0],
        [x-width/2, y-width/2, height],
        [x+width/2, y-width/2, height],
        [x+width/2, y+width/2, height],
        [x-width/2, y+width/2, height]
    ])
    
    faces = [
        [vertices[0], vertices[1], vertices[5], vertices[4]],
        [vertices[1], vertices[2], vertices[6], vertices[5]],
        [vertices[2], vertices[3], vertices[7], vertices[6]],
        [vertices[3], vertices[0], vertices[4], vertices[7]],
        [vertices[4], vertices[5], vertices[6], vertices[7]],
    ]
    
    poly = Poly3DCollection(faces, alpha=alpha, facecolor=color, edgecolor='black', linewidth=0.5)
    ax.add_collection3d(poly)


def plot_open_area(ax):
    """绘制开阔地场景"""
    ax.set_title('开阔地\n$R_{canyon}=0$', fontsize=11, fontweight='bold')
    # 无建筑物，仅地面网格
    for i in range(6):
        for j in range(6):
            ax.plot([i, i+1], [j, j], [0, 0], 'k-', linewidth=0.3, alpha=0.3)
            ax.plot([i, i], [j, j+1], [0, 0], 'k-', linewidth=0.3, alpha=0.3)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_zlim(0, 5)


def plot_low_density(ax):
    """绘制低密度区场景"""
    ax.set_title('低密度区\n$R_{canyon}=0.2$', fontsize=11, fontweight='bold')
    buildings = [(1, 1, 1.5), (4, 3, 2.0)]
    for x, y, h in buildings:
        draw_building(ax, x, y, h)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_zlim(0, 5)


def plot_medium_density(ax):
    """绘制中密度区场景"""
    ax.set_title('中密度区\n$R_{canyon}=0.5$', fontsize=11, fontweight='bold')
    buildings = [
        (1, 1, 2.0), (3, 1, 2.5), (1, 3, 1.8), (4, 3, 2.2),
        (2, 4, 2.0)
    ]
    for x, y, h in buildings:
        draw_building(ax, x, y, h)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_zlim(0, 5)


def plot_high_density(ax):
    """绘制高密度区场景"""
    ax.set_title('高密度区\n$R_{canyon}=0.8$', fontsize=11, fontweight='bold')
    buildings = [
        (0.5, 0.5, 3.0), (2, 0.5, 2.8), (3.5, 0.5, 3.2),
        (0.5, 2, 2.5), (2, 2, 3.0), (3.5, 2, 2.7),
        (0.5, 3.5, 2.8), (2, 3.5, 3.1), (3.5, 3.5, 2.9)
    ]
    for x, y, h in buildings:
        draw_building(ax, x, y, h)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_zlim(0, 5)


def plot_urban_canyon(ax):
    """绘制城市峡谷场景"""
    ax.set_title('城市峡谷\n$R_{canyon}=1.0$', fontsize=11, fontweight='bold')
    # 两侧高楼形成峡谷效应
    for i in range(5):
        draw_building(ax, 0.5, i*1.2, 4.0, color='#566573', alpha=0.8)
        draw_building(ax, 4.5, i*1.2, 4.0, color='#566573', alpha=0.8)
    ax.set_xlim(-0.5, 5.5)
    ax.set_ylim(-0.5, 5.5)
    ax.set_zlim(0, 5)


# ==================== 主绘图程序 ====================
fig = plt.figure(figsize=(14, 5))

scenes = [
    ('open', plot_open_area),
    ('low', plot_low_density),
    ('medium', plot_medium_density),
    ('high', plot_high_density),
    ('canyon', plot_urban_canyon)
]

for idx, (name, plot_func) in enumerate(scenes):
    ax = fig.add_subplot(1, 5, idx+1, projection='3d')
    plot_func(ax)
    
    # 统一视角和样式
    ax.view_init(elev=20, azim=-60)
    ax.set_box_aspect([1, 1, 0.8])
    ax.set_xlabel('X', fontsize=8)
    ax.set_ylabel('Y', fontsize=8)
    ax.set_zlabel('Z', fontsize=8)
    ax.tick_params(labelsize=7)

plt.suptitle('不同城市峡谷复杂度场景的三维示意图', fontsize=13, fontweight='bold', y=0.98)
plt.tight_layout()
plt.show()

# ==================== 打印参数说明 ====================
print("\n" + "="*70)
print("城市建筑因子可视化参数说明")
print("="*70)
print("\nR_canyon 计算公式：")
print("R_canyon = w₁[1-SVF]^α + w₂·H_avg/(z+ε) + w₃·D_building")
print("\n场景参数对比：")
print("-" * 70)
print(f"{'场景':<12} | {'SVF':<8} | {'H_avg(m)':<10} | {'D_building':<12} | {'R_canyon'}")
print("-" * 70)
print(f"{'开阔地':<12} | {'1.0':<8} | {'0':<10} | {'∞':<12} | {'0.0'}")
print(f"{'低密度区':<12} | {'0.8':<8} | {'1.8':<10} | {'较大':<12} | {'0.2'}")
print(f"{'中密度区':<12} | {'0.6':<8} | {'2.1':<10} | {'中等':<12} | {'0.5'}")
print(f"{'高密度区':<12} | {'0.3':<8} | {'2.9':<10} | {'较小':<12} | {'0.8'}")
print(f"{'城市峡谷':<12} | {'0.1':<8} | {'4.0':<10} | {'极小':<12} | {'1.0'}")
print("="*70)
print("\n说明：")
print("- SVF (Sky View Factor): 天空可视因子，0-1之间，值越小表示遮挡越严重")
print("- H_avg: 周围建筑物平均高度")
print("- D_building: 建筑物间距倒数，反映建筑密度")
print("- R_canyon 综合反映城市峡谷的复杂程度和对无人机飞行的影响")
print("="*70)
