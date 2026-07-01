# 图片资源目录 - figures/

## 📸 使用说明

本目录用于存放论文中插入的图片文件。

### 支持的格式

- ✅ **PDF**（推荐）- 矢量图，无限缩放不失真
- ✅ **SVG** - 矢量图，需转换为 PDF
- ✅ **PNG** - 位图，适合照片、截图
- ✅ **JPG/JPEG** - 位图，适合照片
- ⚠️ **EPS** - 仅在使用 `latex + dvipdf` 时需要

### 最佳实践

1. **优先使用矢量图**
   ```python
   # Python matplotlib 示例
   import matplotlib.pyplot as plt
   
   plt.figure(figsize=(8, 6))
   plt.plot([1, 2, 3], [1, 4, 9])
   plt.savefig('figures/plot_example.pdf', format='pdf', bbox_inches='tight')
   ```

2. **图片命名规范**
   - 使用小写字母和下划线
   - 描述性名称
   - 示例：`framework_diagram.pdf`, `results_comparison.png`

3. **分辨率要求**
   - 位图（PNG/JPG）：≥ 300 DPI
   - 矢量图（PDF/SVG）：无限制

4. **尺寸优化**
   - 单栏宽度：~8.5 cm (3.35 inches)
   - 双栏宽度：~17.5 cm (6.89 inches)
   - 高度不超过 23 cm

### 在 LaTeX 中插入图片

```latex
\begin{figure}[t]
    \centering
    \includegraphics[width=\linewidth]{figures/your_image.pdf}
    \caption{图片说明文字}
    \label{fig:your_label}
\end{figure}
```

### 常用工具

- **Python**: matplotlib, seaborn, plotly
- **R**: ggplot2
- **MATLAB**: exportgraphics
- **在线工具**: draw.io, Inkscape, Adobe Illustrator

### 当前状态

📁 此目录目前为空，请添加你的实验图表。

---

**提示**: 编译错误 "File not found" 通常是因为图片未放入此目录或路径错误。
