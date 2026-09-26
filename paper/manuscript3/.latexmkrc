# latexmk 配置（命令行执行 `latexmk -xelatex main.tex` 时自动生效）
# 中文 ctex 方案必须使用 XeLaTeX，故把 pdflatex / xelatex 都指向 xelatex。

# PDF 生成方式：1 = 直接生成 PDF（此处把引擎换成 XeLaTeX）
$pdf_mode = 1;

# 引擎与常用参数：%O 为选项占位，%S 为源文件占位
$xelatex  = 'xelatex -8bit -file-line-error -synctex=1 -interaction=nonstopmode %O %S';
$pdflatex = $xelatex;          # 让 latexmk -pdf 也走 XeLaTeX

# 中间文件统一输出到 build/，源码目录保持干净
$out_dir  = 'build';

# BibTeX 处理（若改用 biblatex + biber，把下面改为 $bibtex = 'biber %O %S'）
$bibtex   = 'bibtex %O %S';

# 自动重跑次数上限：处理交叉引用与文献
$max_repeat = 6;

# 需要清理的中间文件后缀
$clean_ext = 'acn acr alg aux bbl bcf blg brf fdb_latexmk fls glg glo gls idx ilg ind ist lof log lot out run.xml synctex.gz toc';

# 失败时不自动删除辅助文件，方便排错
$cleanup_on_failure = 0;

# 编译完成后不自动打开预览（交给 VS Code）
$preview_mode = 0;
