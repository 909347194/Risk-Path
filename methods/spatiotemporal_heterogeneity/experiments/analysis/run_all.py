"""
一键生成全部结果分析图（缺口1 / 缺口3 / 缺口4）。

每个主题由独立脚本负责，本文件只做编排：

    python run_all.py                  # 全部生成
    python run_all.py --only 缺口1     # 只生成风险分解图
    python run_all.py --only 缺口3     # 只生成约束满足图
    python run_all.py --only 缺口4     # 只生成基线对比图
"""

from __future__ import annotations

import argparse
from pathlib import Path

import plot_baseline_comparison
import plot_constraint_satisfaction
import plot_risk_decomposition

TARGETS = {
    "缺口1": ("沿路径累积风险分量分解", plot_risk_decomposition.main),
    "缺口3": ("安全约束满足可视化", plot_constraint_satisfaction.main),
    "缺口4": ("基线方法系统对比", plot_baseline_comparison.main),
}


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="生成全部结果分析图")
    parser.add_argument("--only", choices=sorted(TARGETS), default=None,
                        help="只生成指定缺口的图")
    args = parser.parse_args(argv)

    targets = [args.only] if args.only else sorted(TARGETS)
    for name in targets:
        desc, func = TARGETS[name]
        print()
        print("#" * 60)
        print(f"# {name} — {desc}")
        print("#" * 60)
        func([])

    print()
    print("=" * 60)
    print("All analysis figures generated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
