#!/bin/bash
# Linux/Mac 编译脚本

set -e  # 遇到错误时退出

echo "========================================"
echo "  LaTeX 论文编译脚本"
echo "========================================"
echo ""

# 创建 build 目录
mkdir -p build

# 使用 latexmk 编译
echo "[1/3] 开始编译..."
latexmk -pdf -outdir=build main.tex

echo ""
echo "[2/3] 编译成功！"
echo "[3/3] PDF 文件位置: build/main.pdf"
echo ""

# 询问是否打开 PDF
read -p "是否打开 PDF 查看？(y/n): " open_pdf
if [ "$open_pdf" = "y" ] || [ "$open_pdf" = "Y" ]; then
    echo "打开 PDF..."
    if command -v xdg-open &> /dev/null; then
        xdg-open build/main.pdf  # Linux
    elif command -v open &> /dev/null; then
        open build/main.pdf      # macOS
    fi
else
    echo "完成。"
fi
