"""
降雨风险因子 f_rain 可视化脚本
==============================
可视化公式：
f_rain(x,y,t) = 1 + γ · I_rain(x,y,t)²

参数设置（参考论文）：
- γ：降雨敏感系数（控制降雨对风险的放大程度）
- I_rain：降水强度（mm/h）
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 设置中文字体（Windows系统）
rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
rcParams['axes.unicode_minus'] = False

# ==================== 参数配置 ====================
gamma_values = [0.001, 0.005, 0.01, 0.02]  # 不同的降雨敏感系数
I_rain_max = 50  # 最大降水强度 (mm/h)

# ==================== 计算降雨风险因子 ====================
# 降水强度范围：0 ~ 50 mm/h
I_rain = np.linspace(0, I_rain_max, 500)

# ==================== 绘图 ====================
fig, ax = plt.subplots(figsize=(8, 5))

# 绘制不同γ值的曲线
colors = ['#2F80ED', '#00A6A6', '#F2994A', '#EB5757']
for gamma, color in zip(gamma_values, colors):
    f_rain = 1 + gamma * I_rain ** 2
    ax.plot(I_rain, f_rain, linewidth=2, color=color, 
            label=r'$\gamma = {:.3f}$'.format(gamma))

# 标注典型降水强度点
typical_rain_points = [
    (5, '小雨'),
    (15, '中雨'),
    (25, '大雨'),
    (40, '暴雨')
]

for I_val, label in typical_rain_points:
    ax.axvline(x=I_val, color='gray', linestyle='--', alpha=0.3)
    for gamma in gamma_values[:2]:  # 只标注前两条曲线
        f_val = 1 + gamma * I_val ** 2
        if gamma == gamma_values[0]:  # 只在第一条曲线上添加文本
            ax.annotate(label, 
                       xy=(I_val, f_val),
                       xytext=(5, 5),
                       textcoords='offset points',
                       fontsize=9,
                       rotation=90,
                       verticalalignment='bottom')

# 设置坐标轴
ax.set_xlabel('降水强度 $I_{rain}$ (mm/h)', fontsize=12)
ax.set_ylabel(r'降雨风险因子 $f_{rain}$', fontsize=12)
ax.set_title(r'降雨风险因子 $f_{rain}$ 随降水强度变化', 
             fontsize=13, fontweight='bold')
ax.legend(loc='upper left', title='降雨敏感系数')
ax.grid(True, alpha=0.3)

# 设置y轴范围
ax.set_ylim(0, max([1 + gamma * I_rain_max ** 2 for gamma in gamma_values]) * 1.1)

plt.tight_layout()

# 保存为PDF矢量图（推荐用于LaTeX论文）
output_path = 'figures/f_rain_curve.pdf'
plt.savefig(output_path, format='pdf', bbox_inches='tight')
print(f"\n已保存矢量图: {output_path}")

plt.show()

# ==================== 打印表格数据 ====================
print("\n" + "="*70)
print("降雨风险因子边界条件验证")
print("="*70)
print(f"{'降水类型':<10} | {'降水强度 I (mm/h)':<18} | {'γ=0.001':<12} | {'γ=0.005':<12} | {'γ=0.01':<12}")
print("-" * 70)

rain_data = [
    ("无雨", 0),
    ("小雨", 5),
    ("中雨", 15),
    ("大雨", 25),
    ("暴雨", 40),
    ("大暴雨", 50)
]

for rain_type, I in rain_data:
    f_vals = []
    for gamma in [0.001, 0.005, 0.01]:
        f_val = 1 + gamma * I ** 2
        f_vals.append(f"{f_val:.3f}")
    
    print(f"{rain_type:<10} | {I:<18.1f} | {f_vals[0]:<12} | {f_vals[1]:<12} | {f_vals[2]:<12}")

print("="*70)
print("\n说明：")
print("- f_rain = 1 表示无降雨影响（基准状态）")
print("- γ 值越大，降雨对风险的放大效应越显著")
print("- 降水强度采用平方关系，体现非线性增长特征")
print("="*70)
