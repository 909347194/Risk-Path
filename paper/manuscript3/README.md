# Manuscript 3 · LaTeX 论文模板（中文 / 单栏）

一份**按合规可维护优先**组织的 LaTeX 稿件骨架：中文（`ctex`）、单栏、`elsarticle` 期刊类、XeLaTeX 编译。
与 `manuscript1/2` 的区别在于：**导言区分层、正文分目录、元信息与内容彻底分离、构建配置外置**，
使得"改元信息不动正文、改排版不动内容、改实验不动算法"。

---

## 1. 环境依赖

| 组件        | 版本/说明                                        |
| ----------- | ------------------------------------------------ |
| TeX Live    | 2023 及以上（含 `latexmk`、`xelatex`、`texcount`）|
| VS Code     | + LaTeX Workshop 扩展（配置已内置在 `.vscode/`）  |
| 编译引擎    | **必须用 XeLaTeX**（中文 `ctex` 不支持 pdfLaTeX） |

> 本模板只使用 TeX Live 默认发行版自带的宏包，不依赖任何需额外安装的包。

---

## 2. 目录结构

```
manuscript3/
├── main.tex                      # 唯一入口：只做编排 + 全局开关，无正文
│
├── preamble/                     # 导言区（分层，顺序敏感）
│   ├── packages.tex              #   宏包集合
│   ├── layout.tex                #   版式、间距、题注、定理环境
│   ├── math-notation.tex         #   ★ 数学符号唯一定义处
│   ├── text-macros.tex           #   术语缩写与文本级宏
│   ├── algorithms.tex            #   伪代码环境中文配置
│   ├── draft-tools.tex           #   TODO / 批注 / 占位图（受 draft 开关控制）
│   └── references-setup.tex      #   hyperref + cleveref（必须最后加载）
│
├── config/                       # 元数据（改这里不影响正文）
│   ├── metadata.tex              #   标题、作者、单位、基金、MSC
│   ├── abstract.tex              #   摘要与关键词
│   └── highlights.tex            #   研究亮点
│
├── body/                         # 正文（编号前缀 = 章节顺序）
│   ├── 01-introduction.tex
│   ├── 02-related-work.tex
│   ├── 03-preliminaries.tex
│   ├── 04-risk-model.tex
│   ├── 05-planning-algorithm.tex
│   ├── 06-experiments.tex
│   ├── 07-discussion.tex
│   └── 08-conclusion.tex
│
├── back/                         # 文末
│   ├── declarations.tex          #   CRediT / 基金 / 利益冲突 / 数据可用性 / AI 声明
│   ├── acknowledgments.tex
│   ├── appendix-a-notation.tex
│   └── appendix-b-supplement.tex
│
├── assets/
│   ├── figures/                  # 插图（含 FIGURES.md 出图规范）
│   └── tables/                   # 独立表格，正文用 \input 引入
│       ├── literature-comparison.tex
│       ├── main-results.tex
│       └── notation.tex
│
├── bib/references.bib            # 参考文献库（建议 Zotero+Better BibTeX 导出）
│
├── .latexmkrc                    # 编译引擎与 clean 规则
├── Makefile                      # pdf / watch / words / check / clean
├── .editorconfig                 # 编辑器统一约定（100 列换行）
├── .gitignore                    # 忽略中间文件，保留矢量图源码
├── .vscode/settings.json         # LaTeX Workshop：outDir=build / latexmk(xelatex)
└── README.md                     # 本文件
```

---

## 3. 快速开始

**VS Code（推荐）**：打开 `main.tex` → 保存即自动编译 → `Ctrl+Alt+V` 预览；`Ctrl+Alt+J` 正向搜索。

**命令行**：

```bash
make pdf         # 编译到 build/main.pdf
make watch       # 实时编译
make words       # 字数统计
make check       # 检查未定义引用/缺失文件
make clean       # 清理中间文件
make distclean   # 连 build/ 一起删除
```

等价于：`latexmk -xelatex -outdir=build main.tex`。

---

## 4. 组织原则（请遵守，否则模板会退化）

1. **`main.tex` 是胶水**：只 `\input`，不写内容、不加宏包；
2. **一处定义，处处引用**：所有数学符号写在 `preamble/math-notation.tex`，同步维护附录符号表；
   所有术语/方法名写成 `\newcommand`（如 `\methodname`），全文替换只改一行；
3. **元数据与正文物理分离**：投稿不同期刊时只改 `config/`，正文零改动；
4. **大表格独立成文件**：`assets/tables/*.tex`，正文 `\input{...}`，减少多人协作冲突；
5. **一张图一个文件**：矢量图优先，禁止往 `figures/` 塞中间产物；
6. **中间文件一律进 `build/`**：源码目录永远干净（`.gitignore` 已覆盖）。

---

## 5. 命名约定

| 对象   | 前缀       | 示例                                  |
| ------ | ---------- | ------------------------------------- |
| 章节   | `sec:`     | `\label{sec:risk-model}`              |
| 图     | `fig:`     | `\label{fig:synthetic}`               |
| 表     | `tab:`     | `\label{tab:main-results}`            |
| 式子   | `eq:`      | `\label{eq:risk-cost}`                |
| 算法   | `alg:`     | `\label{alg:td-risk-astar}`           |
| 定理类 | `thm:`     | `\label{thm:monotone}`                |
| 附录   | `app:`     | `\label{app:notation}`                |
| 文件   | 两位数字   | `04-risk-model.tex`（天然排序）        |

引用请用语义化命令 `\reffig{}`、`\reftab{}`、`\refsec{}`、`\refeq{}`、`\refalg{}`、`\refapp{}`，
或直接使用 `\cref{}`。

> 为什么不用 `\figref` / `\algref` 这类名字？cleveref 会为每个浮动体类型自动生成
> `\algref` 等同系列宏，实测会与 `\newcommand` 冲突。因此统一采用 `\ref*` 前缀。

---

## 6. 常用片段速查

```latex
% 插图（\graphicspath 已设，直接写文件名）
\begin{figure}[t]
  \centering
  \includegraphics[width=0.8\linewidth]{risk-field.pdf}
  \caption{风险场示意。}
  \label{fig:risk-field}
\end{figure}

% 未出图时先占位（draft 模式显示占位框）
\placeholderfig[0.8]{风险场示意，待补}

% 引用
“the method of \citet{}”  /  \citep{}  /  \cref{fig:x,tab:y}

% 单位与数值
\SI{12.5}{\metre\per\second}   \num{1.2e5}   \SIrange{0}{100}{\metre}

% 待办（draft 模式显示在页边）
\todo{这里需要一个定量说明}   \note[张三]{建议再补一组消融}
```

---

## 7. 投稿前检查清单

- [ ] `main.tex` 中把 `\drafttrue` 改为 `\draftfalse`（自动关闭行号与 TODO）
- [ ] 删除或替换所有 `\placeholderfig`
- [ ] 执行 `make check`，确认无 undefined citation / reference
- [ ] `config/metadata.tex` 与 `declarations.tex` 已按目标期刊口径填写
- [ ] 所有图表在灰度打印下仍可区分（字体不小于 8 pt）
- [ ] `references.bib` 中 DOI 完整，无遗留 `ref1/ref2` 之类占位 key

---

## 8. 常见问题

**Q：编译报 `Font ... not found`？**
A：没用 XeLaTeX。请确认 `latexmk -xelatex` 或 VS Code 配方选择的是 `latexmk (XeLaTeX)`。

**Q：中文显示方块或乱码？**
A：源码务必保存为 UTF-8（`.editorconfig` 已约束），并用 XeLaTeX 编译。

**Q：加了新文献但参考文献列表没更新？**
A：执行一次 `make distclean && make pdf`；或用 VS Code 配方里含 bibtex 的那条。

**Q：子图/题注与期刊模板冲突？**
A：`preamble/packages.tex` 中 `subcaption` 与部分期刊类有轻微冲突告警（不影响输出）；
若目标期刊投稿系统报错，删除 `subcaption` 并改用并排 `minipage` + 自定义子图说明。

**Q：想加符号怎么办？**
A：在 `preamble/math-notation.tex` 定义 → 在 `assets/tables/notation.tex` 补一行 → 编译检查。
