"""
analysis 包共享工具：路径常量、绘图样式、结果数据加载。

拆分组织约定（重要）：
- 本文件只负责 IO 与样式，不包含任何具体图表逻辑；
- 每个绘图脚本只负责一个"结果分析"主题，可独立运行：
    plot_risk_decomposition.py       缺口1：沿路径累积风险分量逐步分解
    plot_constraint_satisfaction.py  缺口3：安全约束满足可视化
    plot_baseline_comparison.py      缺口4：基线方法系统对比
- 三个脚本共用本文件的加载函数与配色，保证口径一致、风格统一。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# ============================================================
# 路径常量
# ============================================================
ANALYSIS_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = ANALYSIS_DIR.parent                      # .../experiments
MODULE_ROOT = EXPERIMENTS_DIR.parent                       # .../spatiotemporal_heterogeneity
RESULTS_DIR = MODULE_ROOT / "results"
OUTPUT_BASE = RESULTS_DIR / "analysis_figures"

EXP1_PATHS = RESULTS_DIR / "exp1_temporal" / "paths.json"
EXP1_METRICS = RESULTS_DIR / "exp1_temporal" / "metrics.csv"
EXP5_BASELINE = RESULTS_DIR / "exp5_comprehensive" / "baseline_comparison.csv"
EXP5_SIGNIFICANCE = RESULTS_DIR / "exp5_comprehensive" / "statistical_significance.csv"

# ============================================================
# 实验参数常量
# （与 experiments/common/scenario_builder.load_micro_scenario /
#   build_planner_config("default") 保持一致，改参数时两处同步）
# ============================================================
MICRO_GRID = {
    "nx": 40, "ny": 40, "nz": 12, "nt": 24,
    "dx": 10.0, "dy": 10.0, "dz": 10.0,
    "dt_minutes": 60.0,
}

CONSTRAINTS = {
    "survival_threshold": 0.01,     # P_surv 下限（硬约束）
    "max_climb_rate": 5.0,          # m/s
    "max_descent_rate": 5.0,        # m/s
    "min_altitude": 0.0,            # m（层中心高度下限）
    "max_altitude": float("inf"),   # m（层中心高度上限）
    "max_battery_time": float("inf"),  # s（续航时间预算）
    "uav_speed": 10.0,              # m/s
}

# ============================================================
# 配色（色盲友好，与 paper_figures.py 风格一致）
# ============================================================
COMPONENT_KEYS = ("cum_fatality", "cum_property", "cum_noise")
COMPONENT_COLORS = {
    "cum_fatality": "#C0392B",   # 致死风险 — 深红
    "cum_property": "#E67E22",   # 财产损失 — 橙
    "cum_noise": "#2980B9",      # 噪声成本 — 蓝
}
COMPONENT_LABELS = {
    "cum_fatality": "Fatality risk",
    "cum_property": "Property damage",
    "cum_noise": "Noise cost",
}

TIME_COLORS = {8: "#E74C3C", 12: "#F39C12", 18: "#3498DB", 22: "#8E44AD"}
TIME_LABELS = {
    8: "08:00 (Morning Rush)",
    12: "12:00 (Noon)",
    18: "18:00 (Evening Rush)",
    22: "22:00 (Night)",
}

ALGO_COLORS = {
    "TD-RiskA*": "#C0392B",
    "Static A*": "#2980B9",
    "Distance-only": "#7F8C8D",
}

ALGO_ORDER = ["TD-RiskA*", "Static A*", "Distance-only"]

# 指标方向：True = 越大越好
METRIC_DIRECTION = {
    "final_survival": True,
    "cum_fatality": False,
    "cum_noise": False,
    "path_length": False,
    "runtime_ms": False,
    "nodes_explored": False,
    "objective_cost": False,
}


# ============================================================
# 样式
# ============================================================
def setup_style() -> None:
    """统一的学术图表基础样式。"""
    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "legend.fontsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def save_fig(fig, out_dir: Path, name: str) -> Path:
    """300 DPI 保存并关闭画布。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / name
    fig.savefig(target, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [OK] Saved: {target}")
    return target


def display_label(key: str) -> str:
    """paths.json 的键 -> 图例标签。'18' -> '18:00 departure'，其余原样返回。"""
    key = str(key)
    if key.isdigit():
        return f"{int(key):02d}:00 departure"
    return key


def time_color(key: str) -> str:
    """出发时刻键 -> 时次配色；非数字键/未知时次回退灰色。"""
    return TIME_COLORS.get(int(key), "#555555") if str(key).isdigit() else "#555555"


def label_sort_key(key: str) -> Tuple[int, str]:
    """数字出发时刻按时间排序，其余按字符串排在后面。"""
    key = str(key)
    return (0, f"{int(key):03d}") if key.isdigit() else (1, key)


# ============================================================
# 数据加载
# ============================================================
def load_path_records(json_path: Path) -> Dict[str, Dict[str, Any]]:
    """加载 paths.json 为 {标签: {"coords": [...], "states": [...] | None}}。

    兼容两种历史格式：
    1. exp1 格式：{label: {"coords": [[x,y,z,t], ...], "states": [{...}, ...]}}
    2. exp3 格式：{label: [[x,y,z,t], ...]}（仅坐标，无逐步状态）
    """
    json_path = Path(json_path)
    raw = json.loads(json_path.read_text(encoding="utf-8"))
    records: Dict[str, Dict[str, Any]] = {}
    for key, value in raw.items():
        if isinstance(value, dict) and "coords" in value:
            coords = [tuple(int(v) for v in c) for c in value["coords"]]
            states = value.get("states")
        elif isinstance(value, list):
            coords = [tuple(int(v) for v in c) for c in value]
            states = None
        else:
            continue
        records[str(key)] = {"coords": coords, "states": states}
    return records


def state_series(record: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """把逐步 states 转成 {字段: ndarray}；无 states 时抛异常提示。"""
    states = record.get("states")
    if not states:
        raise ValueError(
            "该 paths.json 记录不含逐步 states（仅有坐标），"
            "无法做累积量分解，请使用 exp1 格式的 paths.json"
        )
    series: Dict[str, np.ndarray] = {}
    for key in states[0].keys():
        series[key] = np.array([float(s.get(key, 0.0)) for s in states], dtype=float)
    return series


def coords_array(record: Dict[str, Any]) -> np.ndarray:
    """坐标列表 -> (N, 4) int 数组 [x, y, z, t]。"""
    return np.asarray(record["coords"], dtype=int)


def read_csv_rows(csv_path: Path) -> List[Dict[str, str]]:
    """读 CSV 为 list[dict]，保留列名字符串值。"""
    csv_path = Path(csv_path)
    with csv_path.open("r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def col_float(rows: Sequence[Dict[str, str]], key: str) -> np.ndarray:
    """提取数值列；空串/缺失 -> nan。"""
    out = np.full(len(rows), np.nan, dtype=float)
    for i, row in enumerate(rows):
        raw = row.get(key, "")
        if raw not in (None, ""):
            out[i] = float(raw)
    return out


def load_baseline_rows(csv_path: Path = EXP5_BASELINE):
    """基线对比 CSV -> (od 顺序, {algorithm: {列: np.ndarray}})。

    数组下标与 od_order 严格对齐（按 od 键控重建，不依赖 CSV 行序）；
    缺失的 (od, algorithm) 组合以 nan / 空串占位并告警。
    """
    rows = read_csv_rows(csv_path)
    if not rows:
        raise ValueError(f"baseline CSV 无数据行: {csv_path}")

    od_order: List[str] = []
    by_od: Dict[str, Dict[str, Dict[str, str]]] = {}
    for row in rows:
        od = row.get("od", "")
        algo = row.get("algorithm", "")
        if od not in by_od:
            by_od[od] = {}
            od_order.append(od)
        by_od[od][algo] = row

    numeric_cols = ("path_length", "objective_cost", "final_survival",
                    "cum_fatality", "cum_noise", "runtime_ms", "nodes_explored")
    columns = [k for k in rows[0].keys() if k not in ("od", "algorithm")]

    parsed: Dict[str, Dict[str, np.ndarray]] = {}
    for algo in sorted({r["algorithm"] for r in rows}):
        parsed[algo] = {}
        for key in columns:
            if key in numeric_cols:
                arr = np.full(len(od_order), np.nan, dtype=float)
                for i, od in enumerate(od_order):
                    raw = by_od.get(od, {}).get(algo, {}).get(key, "")
                    if raw not in (None, ""):
                        arr[i] = float(raw)
                parsed[algo][key] = arr
            else:
                parsed[algo][key] = np.asarray([
                    by_od.get(od, {}).get(algo, {}).get(key, "") for od in od_order
                ])

    missing = [(od, algo) for od in od_order for algo in parsed
               if algo not in by_od.get(od, {})]
    if missing:
        print(f"  [WARN] baseline CSV 缺失组合（nan 占位）: {missing}")
    return od_order, parsed


def load_significance(csv_path: Path = EXP5_SIGNIFICANCE):
    """统计显著性 CSV -> {(od, metric): {"mean": f, "std": f, "n": int}}。"""
    sig: Dict[Tuple[str, str], Dict[str, float]] = {}
    for row in read_csv_rows(csv_path):
        sig[(row["od"], row["metric"])] = {
            "mean": float(row["mean"]),
            "std": float(row["std"]),
            "n": int(float(row["n"])),
        }
    return sig


def improvement_pct(tds: float, base: float, higher_is_better: bool) -> float:
    """TD-RiskA* 相对基线的改进百分比（正数=更好）。基线为 0 时返回 nan。"""
    if not np.isfinite(tds) or not np.isfinite(base) or base == 0:
        return float("nan")
    if higher_is_better:
        return (tds - base) / abs(base) * 100.0
    return (base - tds) / abs(base) * 100.0
