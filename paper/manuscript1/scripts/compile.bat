@echo off
REM Windows 批处理脚本 - 编译 LaTeX 论文

echo ========================================
echo   LaTeX 论文编译脚本
echo ========================================
echo.

REM 检查 build 目录是否存在
if not exist "build" mkdir build

REM 使用 latexmk 编译（启用 SyncTeX 支持反向搜索）
echo [1/4] 开始编译...
latexmk -pdf -synctex=1 -outdir=build main.tex

if %errorlevel% neq 0 (
    echo.
    echo [错误] 编译失败！
    exit /b 1
)

echo.
echo [2/4] 编译成功！
echo [3/4] PDF 文件位置: build\main.pdf
echo.

REM 询问是否打开 PDF
set /p open_pdf="是否打开 PDF 查看？(Y/N): "
if /i "%open_pdf%"=="Y" (
    echo [4/4] 打开 PDF...
    start "" "D:\Software\SumatraPDF\SumatraPDF.exe" "build\main.pdf"
) else (
    echo [完成] 编译结束。
)

echo.
pause
