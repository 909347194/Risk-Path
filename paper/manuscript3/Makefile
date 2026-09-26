# ============================================================================
#  Makefile：命令行一键编译（VS Code 用户可直接看 README 的图形化方式）
#  依赖：TeX Live（含 latexmk + xelatex），可选 texcount（统计字数）
# ============================================================================

MAIN   := main
OUT    := build
PDF     = $(OUT)/$(MAIN).pdf
LOG     = $(OUT)/$(MAIN).log

.PHONY: all pdf watch clean distclean words check help

all: pdf

## 编译（自动处理参考文献与交叉引用，多轮编译由 latexmk 决定）
pdf:
	@mkdir -p $(OUT)
	latexmk -xelatex -outdir=$(OUT) -interaction=nonstopmode -file-line-error $(MAIN).tex

## 监听改动自动重编译（配合外部 PDF 阅读器 + SyncTeX 使用）
watch:
	latexmk -xelatex -pvc -outdir=$(OUT) $(MAIN).tex

## 统计字数/词数（需要 TeX Live 自带 texcount）
words:
	texcount -utf8 -inc $(MAIN).tex

## 检查未定义引用与缺失图表文件
check: pdf
	@echo "--- 未定义引用 ---"
	@grep -o "Citation \`[^\`]*' undefined\|Reference \`[^']*' undefined" $(LOG) | sort -u || echo "无"
	@echo "--- 缺失文件 ---"
	@grep -o "File \`[^']*' not found" $(LOG) | sort -u || echo "无"

## 清理中间文件（保留 PDF）
clean:
	latexmk -c -outdir=$(OUT) $(MAIN).tex

## 彻底清理（含 PDF 与 build 目录）
distclean: clean
	rm -rf $(OUT)

help:
	@echo "make pdf        编译 PDF"
	@echo "make watch      实时编译"
	@echo "make words      统计字数"
	@echo "make check      检查未定义引用/缺失文件"
	@echo "make clean      清理中间文件"
	@echo "make distclean  彻底清理"
