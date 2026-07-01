# LaTeX 论文项目 - Manuscript 1

## 📋 项目说明

本目录包含一篇学术论文的完整 LaTeX 源代码，采用模块化结构便于维护和协作。

核心主线：**"风险机理建模 → 成本数学集成 → 启发式算法求解 → 实验验证"**

## 📁 目录结构

```
manuscript1/
├── main.tex                 # 主入口文件（胶水文件）
├── preamble.tex             # 导言区配置（宏包、自定义命令）
├── config.tex               # 元数据（标题、作者、摘要等）
├── 00_abstract.tex          # 摘要
├── 01_introduction.tex      # 引言
├── 02_methodology.tex       # 方法论
├── 03_results.tex           # 实验结果
├── 04_discussion.tex        # 讨论与分析
├── 05_conclusion.tex        # 结论
├── acknowledgments.tex      # 致谢
├── references.bib           # 参考文献数据库
├── figures/                 # 图片资源（PDF/PNG/EPS）
├── tables/                  # 独立表格文件（可选）
├── supplementary/           # 补充材料
├── scripts/                 # 自动化脚本
├── build/                   # 编译中间文件（已加入 .gitignore）
└── README.md                # 本文件
```

## 🔧 环境依赖

- **TeX Live** 或 **MiKTeX**（推荐 TeX Live 2023+）
- **VS Code** + **LaTeX Workshop** 扩展
- **SumatraPDF**（Windows PDF 查看器，支持 SyncTeX）

### 必需宏包

以下宏包已在 `preamble.tex` 中配置：

- `amsmath`, `amssymb` - 数学公式
- `graphicx` - 图形插入
- `booktabs` - 专业表格
- `hyperref` - 超链接
- `algorithm`, `algpseudocode` - 算法伪代码
- `IEEEtran` - IEEE 论文模板类

## 🚀 编译指令

### 方法 1：使用 VS Code LaTeX Workshop（推荐）

1. 打开 `main.tex`
2. 按 `Ctrl+Alt+B` 编译
3. 按 `Ctrl+Alt+V` 查看 PDF

### 方法 2：命令行编译

```bash
# 使用 latexmk（自动处理 BibTeX 和多轮编译）
latexmk -pdf -outdir=build main.tex

# 清理中间文件
latexmk -c -outdir=build

# 完全清理（包括 PDF）
latexmk -C -outdir=build
```

### 方法 3：手动编译

```bash
xelatex -output-directory=build main.tex
bibtex build/main
xelatex -output-directory=build main.tex
xelatex -output-directory=build main.tex
```

## 📝 写作规范

### 文件组织原则

1. **main.tex**：仅作为胶水文件，保持 < 30 行
2. **分章节文件**：使用 `\input{}` 而非 `\include{}`
3. **编号前缀**：确保文件按正确顺序排序（00_, 01_, ...）
4. **资源隔离**：图片放 `figures/`，补充材料放 `supplementary/`

### 最佳实践

- ✅ 使用矢量图（PDF/SVG）而非位图
- ✅ 参考文献使用 Zotero + Better BibTeX 自动管理
- ✅ 图表标题使用 `\caption{}` 并添加 `\label{}`
- ✅ 交叉引用使用 `\ref{}` 或 `\cref{}`（cleveref）
- ❌ 避免在 main.tex 中编写正文内容
- ❌ 避免将编译中间文件提交到 Git

### 引用示例

```latex
% 智能引用（推荐）
\cref{fig:example} shows...  % 自动生成 "Figure 1"
\cref{tab:results,alg:method} % 自动处理多个引用

% 传统引用
Figure~\ref{fig:example} shows...
```

### 图表插入示例

```latex
\begin{figure}[t]
    \centering
    \includegraphics[width=\linewidth]{figures/example.pdf}
    \caption{Example figure caption.}
    \label{fig:example}
\end{figure}
```

## 🔗 SyncTeX 双向搜索

- **正向搜索**：在 VS Code 中按 `Ctrl+Alt+J`，跳转到 PDF 对应位置
- **反向搜索**：在 SumatraPDF 中双击文本，跳回 VS Code 源码

## 📊 Git 工作流

```bash
# 忽略编译中间文件
echo "build/" >> .gitignore
echo "*.aux" >> .gitignore
echo "*.log" >> .gitignore
# ...（见 .gitignore 文件）

# 提交源代码
git add *.tex *.bib figures/
git commit -m "Add manuscript draft"
```

## 🆘 常见问题

### Q1: 编译报错 "File not found"

**A**: 检查文件路径是否正确，确保使用相对路径。

### Q2: 参考文献未显示

**A**: 需要编译两次：第一次生成 `.aux`，第二次读取 `.bbl`。

### Q3: 中文显示乱码

**A**: 在 `preamble.tex` 中取消注释 `\usepackage{ctex}`。

### Q4: 图片无法显示

**A**: 确保图片格式为 PDF/PNG/JPG，路径相对于 `main.tex`。

## 📞 联系与支持

如有问题，请查阅：

- [LaTeX Workshop 文档](https://github.com/James-Yu/LaTeX-Workshop)
- [TeX Stack Exchange](https://tex.stackexchange.com/)
- [Overleaf 指南](https://www.overleaf.com/learn)

---

**最后更新**: 2026-05-14
**维护者**: 张佳齐 (1202510805)
