#!/usr/bin/env bash
# ============================================================================
# Risk-Path · uv 依赖安装 + 运行验证脚本（Qwen Coder / Linux / macOS / Git-Bash）
#
# 用途：
#   在任意干净环境里，用 uv 按 uv.lock 可复现地装好依赖，并验证核心模块可导入、
#   噪声可视化能跑通（--save 落盘）。
#
# 用法：
#   ./srcipts/setup_uv.sh              # 完整安装（按 uv.lock，含 geopandas/cartopy 等）
#   MINIMAL=1 ./srcipts/setup_uv.sh    # 最小安装（只装 numpy/matplotlib/pyyaml，仅跑可视化）
#
# 前置：bash、curl（用于首次装 uv）、能访问 PyPI（或配置 .env.runtime 里的镜像/代理）。
# ============================================================================
set -euo pipefail

# 项目根 = 本脚本上一级（srcipts -> Risk-Path）
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
echo "[setup] 项目根: $PROJECT_ROOT"

# ---------- 0. 安装 uv（若未安装）----------
if ! command -v uv >/dev/null 2>&1; then
  echo "[setup] 未检测到 uv，正在安装（curl -> astral.sh）..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # 让本会话立即能调用（官方安装脚本默认装到 ~/.local/bin）
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "[setup] uv 版本: $(uv --version)"

# ---------- 1. 注入运行环境变量 ----------
if [ -f .env.runtime ]; then
  set -a; . ./.env.runtime; set +a
  echo "[setup] 已加载 .env.runtime"
fi

# ---------- 2. 准备 venv ----------
# 若已存在 .venv（如 Windows 上原生的）则复用，否则用 uv 创建（对齐 .python-version=3.12）
if [ ! -d .venv ]; then
  echo "[setup] 创建 venv（python 3.12）..."
  uv venv --python 3.12
else
  echo "[setup] 复用已有 .venv"
fi

# 跨平台定位 venv 解释器（Windows=Scripts/python.exe，Linux/macOS=bin/python）
if [ -f .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
elif [ -f .venv/bin/python ]; then PY=.venv/bin/python
else echo "[setup][error] 未找到 venv 解释器"; exit 1; fi

# ---------- 3. 安装依赖 ----------
if [ "${MINIMAL:-0}" = "1" ]; then
  echo "[setup] [最小模式] 仅安装 numpy / matplotlib / pyyaml ..."
  uv pip install --python .venv "numpy>=1.26.0" "matplotlib>=3.8.4" "pyyaml"
else
  echo "[setup] [完整模式] 按 uv.lock 精确还原全部依赖（--frozen）..."
  # 升级依赖时去掉 --frozen，改用 `uv sync` 重新解析。
  uv sync --frozen
fi

# ---------- 4. Linux 容器：补系统原生库 + 中文字体 ----------
if [ "$(uname)" = "Linux" ]; then
  # 完整模式下的地理栈（cartopy/rasterio/pyproj）需要 GEOS/PROJ/GDAL 运行时
  if [ "${MINIMAL:-0}" != "1" ]; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "[setup] 安装地理原生库 libgeos/libproj/libgdal ..."
      sudo apt-get update -y && sudo apt-get install -y \
        libgeos-dev libproj-dev libgdal-dev libspatialindex-dev 2>/dev/null \
        || echo "[warn] apt 安装失败，请手动补齐地理原生库（否则 cartopy/rasterio 导入会报错）"
    else
      echo "[warn] 非 apt 系统，请自行安装 GEOS/PROJ/GDAL 开发库"
    fi
  fi
  # matplotlib 中文标签需要 CJK 字体，否则中文变方块
  if ! fc-list 2>/dev/null | grep -qi "Noto Sans CJK"; then
    if command -v apt-get >/dev/null 2>&1; then
      echo "[setup] 安装 fonts-noto-cjk（中文标签需要）..."
      sudo apt-get install -y fonts-noto-cjk 2>/dev/null \
        || echo "[warn] 无法自动安装 CJK 字体；可改脚本为中文标签或手动装 fonts-noto-cjk"
    fi
  fi
fi

# ---------- 5. 验证：导入核心模块 ----------
echo "[setup] 验证核心模块导入..."
"$PY" - <<'PY'
import sys, numpy as np, matplotlib
matplotlib.use("Agg")
sys.path.insert(0, "methods/spatiotemporal_heterogeneity/src")
from tensor_engine.dynamic_noise import DynamicNoiseCost
from tensor_engine.grid_system import GridSystem, SpatialGridConfig, TemporalGridConfig
print("import OK | numpy", np.__version__, "| matplotlib", matplotlib.__version__)
PY

# ---------- 6. 跑一次噪声可视化（--save 落盘）----------
echo "[setup] 跑一次噪声时空异质性可视化（--save）..."
"$PY" methods/spatiotemporal_heterogeneity/experiments/viz_data/viz_noise.py --save

echo ""
echo "[setup] 完成 ✅"
echo "  出图: methods/spatiotemporal_heterogeneity/output/统计/viz_noise_spatiotemporal.png"
echo "  如需交互弹窗（有显示器时）: 去掉 MPLBACKEND=Agg，运行 viz_noise.py（不带 --save）"
