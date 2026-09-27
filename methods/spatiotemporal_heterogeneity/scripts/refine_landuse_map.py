#!/usr/bin/env python3
"""
土地利用修复（A+）：在方案 A 基础上解决 GLC 交叉验证发现的两个问题。

修复内容:
  1. 道路重烧 —— 弃用 v1「沿线 1/3 格步采样、逢线即烧」的过宽判据，
     改为「格心到路网距离 ≤ 24m（≈½格宽）」，路网取 roadline_clip.shp ∪ osm_roads.geojson。
  2. GLC 回填未定格 ——
     a. 不透水面占比 > 0.5（或多数类为 191/192）→ 补建设用地：
        优先 POI 五分类 argmax（poi_counts.npz），否则 3×3 邻域功能众数；
     b. 多数类为绿地/水域 → 补第 6 类；
     c. 耕地/裸地/填空 → 保持未定。

输出:
  data/02_processed/landuse_map_v2.npy   （修复版）
  data/02_processed/landuse_map.npy      （同步覆盖，供 pipeline 直接使用；v1 可由 git 历史恢复）
  docs/landuse_refine_report.md          （修复前后对比）
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_landuse_map import BBOX, NX, NY  # noqa: E402

PROC = PROJECT_ROOT / "data/02_processed"
ROAD_SHP = PROJECT_ROOT / "data/01_raw/road/roadline_clip.shp"
ROAD_GEOJSON = PROJECT_ROOT / "data/01_raw/road/osm_roads.geojson"
DOC = PROJECT_ROOT / "docs/landuse_refine_report.md"

ROAD_RADIUS_M = 24.0          # ≈ 半格宽
IMPERVIOUS = {191, 192}
GREEN_WATER = {51, 52, 61, 62, 71, 72, 81, 82, 91, 92, 121, 122,
               130, 140, 150, 181, 182, 183, 184, 185, 186, 187, 210}
OUR_NAMES = {0: "未定", 1: "住宅", 2: "商业", 3: "机构", 4: "工业", 5: "道路", 6: "绿地/水域"}
POI_CLASS = {"residential": 1, "office": 2, "institution": 3, "transport": 5, "industrial": 4}

minx, miny, maxx, maxy = BBOX
LAT0 = (miny + maxy) / 2
MX_PER_DEG = 111320.0 * np.cos(np.deg2rad(LAT0))
MY_PER_DEG = 110574.0


def to_m(lon: np.ndarray, lat: np.ndarray):
    return (lon - minx) * MX_PER_DEG, (lat - miny) * MY_PER_DEG


def cell_centers_m():
    xs = minx + (np.arange(NX) + 0.5) * (maxx - minx) / NX
    ys = miny + (np.arange(NY) + 0.5) * (maxy - miny) / NY
    gx, gy = np.meshgrid(xs, ys, indexing="ij")
    return to_m(gx.ravel(), gy.ravel())


def load_road_segments() -> np.ndarray:
    """返回 (N,4) 米坐标线段数组 [x0,y0,x1,y1]，合并两个道路源。"""
    segs = []

    def add_lines(lines):
        for arr in lines:
            arr = np.asarray(arr, dtype=np.float64)
            if arr.ndim != 2 or len(arr) < 2:
                continue
            x, y = to_m(arr[:, 0], arr[:, 1])
            for i in range(len(x) - 1):
                segs.append((x[i], y[i], x[i + 1], y[i + 1]))

    if ROAD_SHP.exists() and ROAD_SHP.stat().st_size > 1000:
        import shapefile
        for enc in ("gbk", "utf-8"):
            try:
                sf = shapefile.Reader(str(ROAD_SHP), encoding=enc)
                break
            except Exception:
                sf = None
        if sf:
            for shp in sf.shapes():
                pts = np.asarray(shp.points, dtype=np.float64)
                if pts.size:
                    add_lines([pts])
    if ROAD_GEOJSON.exists():
        data = json.loads(ROAD_GEOJSON.read_text(encoding="utf-8"))
        for feat in data.get("features", []):
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates")
            if not coords:
                continue
            lines = [coords] if geom.get("type") == "LineString" else coords
            add_lines(lines)

    return np.asarray(segs, dtype=np.float64)


def road_cells(segments: np.ndarray, radius_m: float = ROAD_RADIUS_M) -> np.ndarray:
    """格心到路网最小距离 ≤ radius_m 的格子。"""
    cx, cy = cell_centers_m()
    d2 = np.full(NX * NY, np.inf, dtype=np.float64)
    r2 = radius_m ** 2
    for s in range(0, len(segments), 800):
        blk = segments[s:s + 800]
        ax, ay = blk[:, 0], blk[:, 1]
        abx, aby = blk[:, 2] - ax, blk[:, 3] - ay
        denom = abx * abx + aby * aby
        denom[denom == 0] = 1e-12
        for i in range(len(blk)):
            apx = cx - ax[i]
            apy = cy - ay[i]
            t = np.clip((apx * abx[i] + apy * aby[i]) / denom[i], 0.0, 1.0)
            dx = apx - t * abx[i]
            dy = apy - t * aby[i]
            np.minimum(d2, dx * dx + dy * dy, out=d2)
    return (d2 <= r2).reshape(NX, NY)


def neighbor_mode(grid: np.ndarray, i: int, j: int) -> int:
    """5×5 窗口内按距离加权的功能类众数（仅 1–4 类参与）。"""
    weight = {}
    for di in range(-2, 3):
        for dj in range(-2, 3):
            if di == 0 and dj == 0:
                continue
            x, y = i + di, j + dj
            if 0 <= x < NX and 0 <= y < NY and grid[x, y] in (1, 2, 3, 4):
                w = 1.0 / (1.0 + (di * di + dj * dj) ** 0.5)
                weight[grid[x, y]] = weight.get(grid[x, y], 0.0) + w
    return max(weight, key=weight.get) if weight else 0


def glc_stats(grid: np.ndarray, macro_major: np.ndarray, imp: np.ndarray) -> str:
    n = NX * NY
    built_a = np.isin(grid, [1, 2, 3, 4, 5])  # 注意：6=绿地水域不算建设
    built_g = macro_major == 0
    po = (built_a == built_g).sum() / n
    hit = (built_a & built_g).sum() / max(built_a.sum(), 1)
    rec = (built_a & built_g).sum() / max(built_g.sum(), 1)
    return f"二分类一致率 {po*100:.1f}% | 建设命中率 {hit*100:.1f}% | 不透水面召回 {rec*100:.1f}%"


def per_class_lines(grid: np.ndarray, macro_major: np.ndarray, imp: np.ndarray, label: str) -> list[str]:
    out = [f"\n### 逐类证据（{label}）", "| 类别 | 格数 | GLC不透水面多数类占比 | 格内不透水面像素均值 |", "|---|---|---|---|"]
    for c in range(7):
        m = grid == c
        if not m.any():
            continue
        gi = ((macro_major == 0) & m).sum() / m.sum()
        f = float(np.nanmean(imp[m]))
        out.append(f"| {c} {OUR_NAMES[c]} | {int(m.sum())} | {gi*100:.1f}% | {f:.2f} |")
    return out


def main() -> None:
    a = np.load(PROC / "landuse_map.npy").astype(np.int32)
    major = np.load(PROC / "landcover_fcs10_100x100.npy").astype(np.int32)
    imp = np.load(PROC / "landcover_impervious_frac_100x100.npy").astype(np.float32)
    macro_major = np.where(np.isin(major, list(IMPERVIOUS)), 0,
                           np.where(np.isin(major, list(GREEN_WATER)), 1, 2))

    poi = np.load(PROC / "poi_counts.npz")
    poi_stack = {k: poi[k] for k in POI_CLASS if k in poi.files}

    # ── 1. 道路重烧 ──────────────────────────────────────────────────
    segs = load_road_segments()
    print(f"[路网] 线段 {len(segs)} 条（roadline_clip ∪ osm_roads）")
    rmask = road_cells(segs)
    v2 = a.copy()
    n_old_road = int((a == 5).sum())
    v2[a == 5] = 0
    v2[rmask & (v2 == 0)] = 5
    print(f"[道路] v1 {n_old_road} 格 -> v2 {int((v2==5).sum())} 格（判据: 格心距路网≤{ROAD_RADIUS_M:.0f}m）")

    # ── 2. GLC 回填未定格 ────────────────────────────────────────────
    built_fill = ((imp > 0.5) | np.isin(major, list(IMPERVIOUS))) & (v2 == 0)
    green_fill = np.isin(major, list(GREEN_WATER)) & (v2 == 0) & ~built_fill

    n_poi_fill = n_nb_fill = 0
    for i, j in zip(*np.where(built_fill)):
        cats = {k: poi_stack[k][i, j] for k in poi_stack}
        best = max(cats, key=cats.get) if cats and max(cats.values()) > 0 else None
        if best is not None:
            v2[i, j] = POI_CLASS[best]
            n_poi_fill += 1
        else:
            m = neighbor_mode(v2, int(i), int(j))
            if m:
                v2[i, j] = m
                n_nb_fill += 1
    v2[green_fill] = 6
    print(f"[GLC回填] 建设格 {int(built_fill.sum())}（POI 语义 {n_poi_fill} / 邻域众数 {n_nb_fill} / 保持未定 {int(built_fill.sum())-n_poi_fill-n_nb_fill}）")
    print(f"[GLC回填] 绿地水域格 {int(green_fill.sum())} -> 6")

    # ── 3. 保存 + 前后对比 ───────────────────────────────────────────
    np.save(PROC / "landuse_map_v2.npy", v2)
    np.save(PROC / "landuse_map.npy", v2)

    lines = ["# 土地利用修复（A+）报告\n", "## 修复内容\n",
             "1. 道路重烧：格心到路网距离 ≤ 24m（路网 = roadline_clip ∪ osm_roads），替代 v1 沿线采样过烧判据\n",
             "2. GLC_FCS30 回填未定格：不透水面格补建设功能（POI argmax → 邻域众数），绿地水域格补第 6 类\n",
             "## 类别分布对比\n", "| 类别 | v1 (A) | v2 (A+) |", "|---|---|---|"]
    for c in range(7):
        lines.append(f"| {c} {OUR_NAMES[c]} | {int((a==c).sum())} | {int((v2==c).sum())} |")
    lines += ["\n## GLC 交叉验证对比\n",
              f"- v1 (A)：{glc_stats(a, macro_major, imp)}",
              f"- v2 (A+)：**{glc_stats(v2, macro_major, imp)}**"]
    lines += per_class_lines(a, macro_major, imp, "v1 (A)")
    lines += per_class_lines(v2, macro_major, imp, "v2 (A+)")
    lines += ["\n> 注：v2 的回填步骤使用了 GLC 作为数据源，v2 与 GLC 的一致性含自证成分，"
              "仅逐类证据中建筑类（1–4）数字为独立验证；道路类（5）建议看不透水面像素均值，"
              "GLC 多数类对“穿行道路的格子”天然不利（道路宽度仅占格宽 1/3）。"]
    unused = int(((v2 == 0)).sum())
    lines.append(f"\n## 残余\n- 仍未定 {unused} 格（GLC 多数类为耕地/裸地/填空，六类编码中无对应项）")
    lines.append(f"\n> v1 由 `build_landuse_map.py` 可完全重建（git 历史亦保留）；v2 由本脚本生成。")
    DOC.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("v1 (A)  :", glc_stats(a, macro_major, imp))
    print("v2 (A+) :", glc_stats(v2, macro_major, imp))
    for lbl, g in (("v1", a), ("v2", v2)):
        m5 = g == 5
        if m5.any():
            print(f"[道路类 {lbl}] 格数 {int(m5.sum())} | 格内不透水面像素均值 {float(np.nanmean(imp[m5])):.2f} | 多数类不透水面占比 {float(((macro_major==0)&m5).sum()/m5.sum())*100:.1f}%")
    vals, cnts = np.unique(v2, return_counts=True)
    print("v2 分布:", dict(zip(vals.tolist(), cnts.tolist())))
    print(f"[写出] {PROC/'landuse_map_v2.npy'} / landuse_map.npy / {DOC}")


if __name__ == "__main__":
    main()
