#!/usr/bin/env python3
"""
土地利用合成（方案 A/B）× GLC_FCS30 土地覆盖 交叉验证。

输入:
  data/01_raw/land_cover/land_cover.tif        GLC_FCS30 (FCS10 编码, ~10m)
  data/02_processed/landuse_map.npy            方案 A（建筑五类+路网烧录）
  data/02_processed/landuse_map_b.npy          方案 B（OSM landuse，可选对照）
  data/02_processed/landuse_map_c.npy          方案 C（POI 反推，可选对照）

输出:
  data/02_processed/landcover_fcs10_100x100.npy        逐格多数类
  data/02_processed/landcover_impervious_frac_100x100.npy  逐格不透水面占比
  docs/land_cover_cross_validation.md                  验证报告

GLC → 宏观类别交叉映射:
  IMPERVIOUS  = {191 城镇不透水面, 192 乡村不透水面}
  GREEN_WATER = 森林/灌丛/草地/苔藓/稀疏植被/湿地/水体 全部子类
  OTHER       = 耕地(11,12,20)、裸地(200)、冰雪(220)、填充值(0)

网格约定与 build_landuse_map.py 完全一致（BBOX + NX/NY + int((x-minx)/Δx*NX)）。
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_landuse_map import BBOX, NX, NY  # noqa: E402

LANDCOVER_TIF = PROJECT_ROOT / "data/01_raw/land_cover/land_cover.tif"
OUT_DIR = PROJECT_ROOT / "data/02_processed"
DOC = PROJECT_ROOT / "docs/land_cover_cross_validation.md"

IMPERVIOUS = {191, 192}
GREEN_WATER = {
    51, 52, 61, 62, 71, 72, 81, 82, 91, 92,   # 森林
    121, 122,                                  # 灌丛
    130, 140, 150,                             # 草地/苔藓/稀疏植被
    181, 182, 183, 184, 185, 186, 187,         # 湿地
    210,                                       # 水体
}
OTHER = {11, 12, 20, 200, 220, 0}

OUR_NAMES = {0: "未定", 1: "住宅", 2: "商业", 3: "机构", 4: "工业", 5: "道路", 6: "绿地/水域"}
MACRO = ["不透水面", "绿地/水域", "其他(耕地/裸地/填空)"]


def macro(code: int) -> int:
    if code in IMPERVIOUS:
        return 0
    if code in GREEN_WATER:
        return 1
    return 2


def main() -> None:
    import rasterio

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. 读 GLC，逐像素落到 100×100 格 ─────────────────────────────
    with rasterio.open(LANDCOVER_TIF) as src:
        lc = src.read(1)
        T = src.transform
        h, w = lc.shape
        rows, cols = np.mgrid[0:h, 0:w]
        xs, ys = rasterio.transform.xy(T, rows.ravel(), cols.ravel())  # 像素中心
        xs = np.asarray(xs).reshape(h, w)
        ys = np.asarray(ys).reshape(h, w)

    minx, miny, maxx, maxy = BBOX
    ix = ((xs - minx) / (maxx - minx) * NX).astype(np.int32)
    iy = ((ys - miny) / (maxy - miny) * NY).astype(np.int32)
    valid = (ix >= 0) & (ix < NX) & (iy >= 0) & (iy < NY)

    lc_v = lc[valid]
    ix_v, iy_v = ix[valid], iy[valid]

    # 逐格多数类 + 不透水面占比
    major = np.zeros((NX, NY), dtype=np.int32)
    imp_frac = np.zeros((NX, NY), dtype=np.float32)
    for code in np.unique(lc_v):
        m = lc_v == code
        np.add.at(imp_frac, (ix_v[m], iy_v[m]), float(code in IMPERVIOUS))
    # 计数矩阵（格 × 类别）求多数
    cells = ix_v * NY + iy_v
    n_cells = NX * NY
    classes = np.unique(lc_v)
    counts = np.zeros((n_cells, len(classes)), dtype=np.int32)
    for k, code in enumerate(classes):
        m = lc_v == code
        np.add.at(counts[:, k], cells[m], 1)
    major = classes[counts.argmax(axis=1)].reshape(NX, NY).astype(np.int32)
    total_px = np.bincount(cells, minlength=n_cells).reshape(NX, NY)
    with np.errstate(invalid="ignore", divide="ignore"):
        imp_frac = np.where(total_px > 0, imp_frac / np.maximum(total_px, 1), np.nan)

    np.save(OUT_DIR / "landcover_fcs10_100x100.npy", major)
    np.save(OUT_DIR / "landcover_impervious_frac_100x100.npy", imp_frac)

    # ── 2. 与 方案 A/B/C 对比 ─────────────────────────────────────────
    a = np.load(OUT_DIR / "landuse_map.npy").astype(np.int32)
    assert a.shape == (NX, NY), f"landuse_map shape {a.shape}"

    macro_major = np.vectorize(macro)(major)

    lines = []
    lines.append("# 土地利用合成 × GLC_FCS30 土地覆盖 交叉验证报告\n")
    lines.append(f"- 覆盖源：`land_cover.tif`（GLC_FCS30 FCS10 编码，10m 分辨率，"
                 f"{h}×{w} px，落在网格内 {int(valid.sum())} px）")
    lines.append(f"- 网格：BBOX=({minx:.6f},{miny:.6f},{maxx:.6f},{maxy:.6f})，{NX}×{NY}\n")

    def cross_tab(target: np.ndarray, name: str) -> list[str]:
        out = [f"\n## {name}\n"]
        out.append("逐格多数类交叉表（行=合成，列=GLC 宏观类）：\n")
        out.append("| 合成 \\ GLC | 不透水面 | 绿地/水域 | 其他 | 合计 |")
        out.append("|---|---|---|---|---|")
        tot = 0
        agree = 0
        for c in range(7):
            m = target == c
            if not m.any():
                continue
            row = [int(((macro_major == k) & m).sum()) for k in range(3)]
            out.append(f"| {c} {OUR_NAMES[c]} | {row[0]} | {row[1]} | {row[2]} | {m.sum()} |")
        return out

    lines += cross_tab(a, "方案 A（建筑五类+路网） vs GLC")

    # 2.1 不透水面一致性（2×2，合成{1..5}=建设 vs GLC 不透水面多数类）
    built_a = a >= 1
    built_g = macro_major == 0
    n = NX * NY
    po = (built_a == built_g).sum() / n
    pe = (built_a.sum() * built_g.sum() + (~built_a).sum() * (~built_g).sum()) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    lines.append(f"\n### 建设用地二分类一致性（A 的 1–5 类 vs GLC 不透水面）\n")
    lines.append(f"- 总体一致率 **{po*100:.1f}%**，Cohen's κ = **{kappa:.3f}**")
    hit = (built_a & built_g).sum()
    lines.append(f"- 合成判定建设 {int(built_a.sum())} 格中 {hit} 格落在 GLC 不透水面（命中率 {hit/max(built_a.sum(),1)*100:.1f}%）")
    hit2 = (built_a & built_g).sum()
    lines.append(f"- GLC 不透水面 {int(built_g.sum())} 格中被合成判为建设 {hit2} 格（召回 {hit2/max(built_g.sum(),1)*100:.1f}%）")

    # 2.2 逐类命中率 + 不透水面占比
    lines.append("\n### 逐类统计（方案 A）\n")
    lines.append("| 类别 | 格数 | GLC不透水面占比 | GLC绿地水域占比 | 格内不透水面像素均值 |")
    lines.append("|---|---|---|---|---|")
    for c in range(7):
        m = a == c
        if not m.any():
            continue
        gi = ((macro_major == 0) & m).sum() / m.sum()
        gg = ((macro_major == 1) & m).sum() / m.sum()
        f = np.nanmean(imp_frac[m])
        lines.append(f"| {c} {OUR_NAMES[c]} | {int(m.sum())} | {gi*100:.1f}% | {gg*100:.1f}% | {f:.2f} |")

    # 2.3 未定格漏判分析
    m0 = a == 0
    if m0.any():
        f0 = imp_frac[m0]
        lines.append(f"\n### 未定格（{int(m0.sum())} 格）诊断\n")
        lines.append(f"- 不透水面像素均值 {np.nanmean(f0):.2f}；其中 {int((f0>0.5).sum())} 格过半为不透水面"
                     f"（**疑似漏判的建设用地**，{int((f0>0.5).sum())/m0.sum()*100:.1f}%）")
        lines.append(f"- {int(((macro_major==1)&m0).sum())} 格多数类为绿地/水域（可补第 6 类）")
        lines.append(f"- {int(((macro_major==2)&m0).sum())} 格多数类为耕地/裸地/填空")

    # 2.4 方案 B 对照（若有）
    b_path = OUT_DIR / "landuse_map_b.npy"
    if b_path.exists():
        b = np.load(b_path).astype(np.int32)
        built_b = b >= 1
        pob = (built_b == built_g).sum() / n
        lines.append("\n## 方案 B（OSM landuse） vs GLC\n")
        m6 = b == 6
        if m6.any():
            g6 = ((macro_major == 1) & m6).sum() / m6.sum()
            lines.append(f"- B 的 6 类绿地水域 {int(m6.sum())} 格，GLC 多数类同为绿地/水域的占 **{g6*100:.1f}%**")
        bb = b >= 1
        gb = (bb & built_g).sum() / max(bb.sum(), 1)
        lines.append(f"- B 的 1–5 类 {int(bb.sum())} 格落在 GLC 不透水面的占 **{gb*100:.1f}%**；总体二分类一致率 {pob*100:.1f}%")

    # 2.5 A/B 各自与 GLC 的宏观一致率
    def macro_agree(target: np.ndarray) -> float:
        # 仅在双方都有明确语义的格上比较（合成非0）
        m = target > 0
        tg = np.where(target[m] == 6, 1, 0)  # 1-5→0不透水, 6→1绿地水域
        gg2 = macro_major[m]
        ok = ((tg == 0) & (gg2 == 0)) | ((tg == 1) & (gg2 == 1))
        return ok.mean() if m.any() else float("nan")

    lines.append(f"\n## 汇总\n")
    lines.append(f"- A（非未定格）与 GLC 宏观语义一致率：**{macro_agree(a)*100:.1f}%**")
    if b_path.exists():
        lines.append(f"- B（非未定格）与 GLC 宏观语义一致率：**{macro_agree(b)*100:.1f}%**")

    DOC.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[写出] {DOC}")
    print(f"[写出] {OUT_DIR/'landcover_fcs10_100x100.npy'} / landcover_impervious_frac_100x100.npy")


if __name__ == "__main__":
    main()
