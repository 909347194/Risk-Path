@echo off
REM Generate sample figure for LaTeX paper
cd /d "%~dp0"
echo Generating sample figure...
uv run python generate_sample_figure.py
if %errorlevel% equ 0 (
    echo.
    echo Success! Files generated:
    dir results_visualization.*
) else (
    echo.
    echo Error occurred during generation.
)
pause
