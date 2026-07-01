"""
风场因子 f_wind 可视化脚本
==========================
可视化公式：
f_wind = exp(k_w * (v_wind / V_limit)^θ),  当 v_wind < V_limit
f_wind = +∞,                                 当 v_wind >= V_limit

参数设置（参考论文表1）：
- k_w = 3
- θ = 2
- V_limit = 12.0 m/s（6级风上限）
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体（Windows系统）
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False

# ==================== 参数配置 ====================
k_w = 3.0          # 风速敏感度系数
theta = 2.0        # 非线性指数
V_limit = 12.0     # 抗风极限 (m/s)，对应6级风上限

# ==================== 计算风场因子 ====================
# 风速范围：0 ~ V_limit + 2 (包含超限区域)
v_wind = np.linspace(0, V_limit + 2, 500)
f_wind = np.zeros_like(v_wind)

# 计算 f_wind
for i, v in enumerate(v_wind):
    if v < V_limit:
        f_wind[i] = np.exp(k_w * (v / V_limit) ** theta)
    else:
        f_wind[i] = np.nan  # 超限部分用 NaN 表示无穷大

# ==================== 绘图 ====================
fig, ax = plt.subplots(figsize=(8, 5))

# 绘制主曲线
ax.plot(v_wind, f_wind, 'b-', linewidth=2, label=r'$f_{wind}$')

# 标注关键风速点（蒲福风级对应值）
beaufort_points = [
    (2.0, '0-2级'),
    (4.5, '3级'),
    (6.5, '4级'),
    (9.0, '5级'),
    (12.0, '6级')
]

for v, label in beaufort_points:
    f_val = np.exp(k_w * (v / V_limit) ** theta)
    ax.axvline(x=v, color='gray', linestyle='--', alpha=0.3)
    ax.plot(v, f_val, 'ro', markersize=6)
    ax.annotate(f'{label}\n{f_val:.2f}', 
                xy=(v, f_val),
                xytext=(8, 8),
                textcoords='offset points',
                fontsize=9,
                arrowprops=dict(arrowstyle='->', color='red', alpha=0.6))

# 添加抗风极限垂直线
ax.axvline(x=V_limit, color='red', linestyle='-.', linewidth=2, alpha=0.7)
ax.text(V_limit + 0.1, ax.get_ylim()[1] * 0.9, 
        r'$V_{limit}$', fontsize=12, color='red', fontweight='bold')

# 填充安全/危险区域
ax.axvspan(0, V_limit, alpha=0.1, color='green', label='安全区域')
ax.axvspan(V_limit, v_wind[-1], alpha=0.1, color='red', label='失控区域')

# 设置坐标轴
ax.set_xlabel('风速 $v_{wind}$ (m/s)', fontsize=12)
ax.set_ylabel(r'风场因子 $f_{wind}$', fontsize=12)
ax.set_title(r'风场因子 $f_{wind}$ 随风速变化曲线 ($k_w=3, \theta=2, V_{limit}=12m/s$)', 
             fontsize=13, fontweight='bold')
ax.legend(loc='upper left')
ax.grid(True, alpha=0.3)

# 设置y轴范围（避免无穷大影响显示）
ax.set_ylim(0, 25)

plt.tight_layout()

# 保存为PDF矢量图（推荐用于LaTeX论文）
output_path = 'figures/f_wind_curve.pdf'
plt.savefig(output_path, format='pdf', bbox_inches='tight')
print(f"\n已保存矢量图: {output_path}")

plt.show()

# ==================== 打印表格数据 ====================
print("\n" + "="*60)
print("风场因子边界条件验证 (k_w=3, θ=2)")
print("="*60)
print(f"{'蒲福风级':<10} | {'典型风速 v (m/s)':<18} | {'无量纲比 v/V_limit':<18} | {'f_wind':<10}")
print("-" * 60)

beaufort_data = [
    ("0-2 级", 2.0),
    ("3 级", 4.5),
    ("4 级", 6.5),
    ("5 级", 9.0),
    ("6 级", 12.0),
    ("≥7 级", 13.0)
]

for level, v in beaufort_data:
    ratio = v / V_limit
    if v < V_limit:
        f_val = np.exp(k_w * (v / V_limit) ** theta)
        print(f"{level:<10} | {v:<18.1f} | {ratio:<18.2f} | {f_val:.2f}")
    else:
        print(f"{level:<10} | {v:<18.1f} | {ratio:<18.2f} | +∞")

print("="*60)
