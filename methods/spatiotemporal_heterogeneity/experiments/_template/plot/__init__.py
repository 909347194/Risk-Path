#!/usr/bin/env python3
"""实验可视化层（plot 包）：所有图表职责集中在此，对外导出 plot_fig* 函数。

约定：
- 每张图一个模块：plot/figN_xxx.py，函数签名 `plot_figN(..., out_path)`
- 只做可视化，不做计算/IO（数据由 run.py 算好传入）
- 统一 matplotlib Agg 后端，fig.savefig 后 plt.close(fig)
"""
from plot.fig1_example import plot_fig1

__all__ = ["plot_fig1"]
