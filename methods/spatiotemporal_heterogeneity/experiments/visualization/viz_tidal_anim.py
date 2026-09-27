#!/usr/bin/env python3
"""
潮汐动画可视化（rho_pop_3d / rho_vehicle_3d，96 时相 = 24h × 15min）

动态播放人口潮汐与车辆潮汐的空间演变，可直接看出早晚高峰的"呼吸"效应。

- 左：人口潮汐 ρ_pop
- 右：车辆潮汐 ρ_veh
- 色标固定（全局最大值），保证不同时刻可比

用法：
  python3 viz_tidal_anim.py                 # 弹窗播放（可拖动/暂停）
  python3 viz_tidal_anim.py --gif out.gif   # 另存 GIF（便于无显示器环境查看）
  python3 viz_tidal_anim.py --fps 12        # 调整播放速度

数组轴序 [ix, iy, t]，显示需转置前两维。
"""
import argparse
import warnings
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Noto Sans CJK SC", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
# 无 GUI 后端（如 Agg 冒烟测试）下动画不渲染即退出会告警，无害，屏蔽之
warnings.filterwarnings("ignore", message="Animation was deleted without rendering")

PROC = Path(__file__).resolve().parents[2] / "data" / "02_processed"
MINX, MINY, MAXX, MAXY = 113.2910928837698, 23.073499711374893, 113.33841698453455, 23.116852006517036
EXTENT = [MINX, MAXX, MINY, MAXY]
NT = 96
_ANIM = None  # 模块级引用，防止 Animation 被回收


def hhmm(t: int) -> str:
    """时相 -> 时刻（96 时相覆盖一天）"""
    return f"{t * 24 // NT:02d}:{t * 60 * 24 // NT % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", help="保存为 GIF 路径（不给则弹窗播放）")
    ap.add_argument("--fps", type=float, default=10, help="播放帧率")
    ap.add_argument("--step", type=int, default=1, help="抽帧步长（2=隔帧，文件更小）")
    args = ap.parse_args()

    rp = np.load(PROC / "rho_pop_3d.npy").astype(float)     # (100,100,96)
    rv = np.load(PROC / "rho_vehicle_3d.npy").astype(float)

    frames = range(0, NT, max(1, args.step))
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))

    im0 = axes[0].imshow(rp[:, :, 0].T, origin="lower", extent=EXTENT,
                         cmap="YlOrRd", vmin=0, vmax=rp.max())
    axes[0].set_title("人口潮汐 ρ_pop", fontsize=11)
    fig.colorbar(im0, ax=axes[0], fraction=0.046)

    im1 = axes[1].imshow(rv[:, :, 0].T, origin="lower", extent=EXTENT,
                         cmap="YlGnBu", vmin=0, vmax=rv.max())
    axes[1].set_title("车辆潮汐 ρ_veh", fontsize=11)
    fig.colorbar(im1, ax=axes[1], fraction=0.046)

    for ax in axes:
        ax.set_xlabel("经度 (°E)")
        ax.set_ylabel("纬度 (°N)")
    title = fig.suptitle("", fontsize=13)
    fig.tight_layout()

    def update(t):
        im0.set_data(rp[:, :, t].T)
        im1.set_data(rv[:, :, t].T)
        title.set_text(f"潮汐密度动态   t={t}/95   {hhmm(t)}")
        return im0, im1, title

    ani = FuncAnimation(fig, update, frames=list(frames), interval=1000 / args.fps, blit=False)

    if args.gif:
        print(f"正在渲染 GIF（{len(list(frames))} 帧）...")
        ani.save(args.gif, writer=PillowWriter(fps=args.fps), dpi=80)
        print("已保存:", args.gif)
    else:
        # 模块级引用，防止 Animation 被回收（无 GUI 后端下仅告警，交互后端下会中断播放）
        global _ANIM
        _ANIM = ani
        plt.show()


if __name__ == "__main__":
    main()
