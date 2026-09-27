#!/usr/bin/env python3
"""
土地利用交叉验证：方案 B（OSM Overpass）/ 方案 C（POI 反推）与方案 A 对比。

- B：Overpass 抓研究区 landuse/amenity/leisure/natural/highway 面点要素，
   烧录 landuse_map_b.npy（缓存原始 GeoJSON 到 data/01_raw/landuse/osm_landuse.geojson）
- C：由 poi_counts.npz（五分类计数）逐格 argmax 反推 landuse_map_c.npy
- 对比图 docs/figures/landuse_crossval.png + 一致性统计

编码同 build_landuse_map.py：0=未定 1=住宅 2=商业 3=机构 4=工业 5=道路 6=绿地/水域
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_landuse_map import BBOX, NX, NY  # noqa: E402

OVERPASS = "https://overpass-api.de/api/interpreter"
RAW_DIR = PROJECT_ROOT / "data" / "01_raw" / "landuse"
CACHE = RAW_DIR / "osm_landuse.geojson"
OUT_B = PROJECT_ROOT / "data" / "02_processed" / "landuse_map_b.npy"
OUT_C = PROJECT_ROOT / "data" / "02_processed" / "landuse_map_c.npy"
POI_COUNTS = PROJECT_ROOT / "data" / "02_processed" / "poi_counts.npz"
FIG_DIR = PROJECT_ROOT / "docs" / "figures"
FIG = FIG_DIR / "landuse_crossval.png"

AMENITY_3 = ("school", "university", "college", "kindergarten", "hospital", "clinic",
             "townhall", "police", "library", "courthouse", "fire_station")

QUERY = f"""[out:json][timeout:120];
(
  way["landuse"~"^(residential|commercial|retail|industrial|quarry)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  relation["landuse"~"^(residential|commercial|retail|industrial|quarry)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["amenity"~"^({'|'.join(AMENITY_3)})$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  node["amenity"~"^({'|'.join(AMENITY_3)})$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["leisure"~"^(park|garden|pitch|playground)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["natural"~"^(water|wood|scrub)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["landuse"~"^(grass|forest|meadow)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["building"~"^(industrial|warehouse)$"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
  way["highway"]({BBOX[1]},{BBOX[0]},{BBOX[3]},{BBOX[2]});
);
out geom;"""


def tag_code(tags: dict) -> int:
    landuse = tags.get("landuse", "")
    amenity = tags.get("amenity", "")
    leisure = tags.get("leisure", "")
    natural = tags.get("natural", "")
    building = tags.get("building", "")
    if tags.get("highway"):
        return 5
    if landuse == "residential":
        return 1
    if landuse in ("commercial", "retail"):
        return 2
    if amenity in AMENITY_3:
        return 3
    if landuse in ("industrial", "quarry") or building in ("industrial", "warehouse"):
        return 4
    if leisure in ("park", "garden", "pitch", "playground") or natural in ("water", "wood", "scrub") or landuse in ("grass", "forest", "meadow"):
        return 6
    return 0


def fetch_osm() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({"data": QUERY}).encode()
    headers = {
        "User-Agent": "risk-path-landuse-crossval/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    for host in (
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ):
        try:
            req = urllib.request.Request(host, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.load(resp)
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"[B] Overpass 抓取成功（{host}），元素 {len(payload.get('elements', []))} 个")
            return payload
        except Exception as exc:
            print(f"[B] {host} 失败: {exc}")
    raise RuntimeError("Overpass 全部镜像失败")


def mark_cell(grid: np.ndarray, x: float, y: float, code: int) -> None:
    minx, miny, maxx, maxy = BBOX
    if not (minx <= x <= maxx and miny <= y <= maxy):
        return
    ix = min(NX - 1, int((x - minx) / (maxx - minx) * NX))
    iy = min(NY - 1, int((y - miny) / (maxy - miny) * NY))
    if grid[ix, iy] == 0 or code == 5 and grid[ix, iy] == 0:
        grid[ix, iy] = code


def rasterize_b(payload: dict) -> np.ndarray:
    grid = np.zeros((NX, NY), dtype=np.int32)
    minx, miny, maxx, maxy = BBOX
    step = (maxx - minx) / NX / 3
    codes = Counter()
    for el in payload.get("elements", []):
        code = tag_code(el.get("tags", {}))
        if code == 0:
            continue
        codes[code] += 1
        if el.get("type") == "node" and "lat" in el:
            mark_cell(grid, el["lon"], el["lat"], code)
            continue
        geom = el.get("geometry") or []
        pts = [(p["lon"], p["lat"]) for p in geom]
        if len(pts) < 2:
            continue
        arr = np.asarray(pts, dtype=np.float64)
        # 面：格心命中；线/面均做边界采样补格
        if el.get("type") in ("way", "relation") and arr[0][0] == arr[-1][0] and arr[0][1] == arr[-1][1] and len(arr) >= 4:
            i0 = max(0, int((arr[:, 0].min() - minx) / (maxx - minx) * NX) - 1)
            i1 = min(NX, int((arr[:, 0].max() - minx) / (maxx - minx) * NX) + 2)
            j0 = max(0, int((arr[:, 1].min() - miny) / (maxy - miny) * NY) - 1)
            j1 = min(NY, int((arr[:, 1].max() - miny) / (maxy - miny) * NY) + 2)
            if i0 < i1 and j0 < j1:
                gx, gy = np.meshgrid(
                    minx + (np.arange(i0, i1) + 0.5) * (maxx - minx) / NX,
                    miny + (np.arange(j0, j1) + 0.5) * (maxy - miny) / NY,
                    indexing="ij",
                )
                inside = MplPath(arr).contains_points(np.column_stack([gx.ravel(), gy.ravel()]))
                ii, jj = np.meshgrid(np.arange(i0, i1), np.arange(j0, j1), indexing="ij")
                sel = inside.reshape(ii.shape)
                grid[ii[sel], jj[sel]] = code
        for (x0, y0), (x1, y1) in zip(arr[:-1], arr[1:]):
            dist = max(abs(x1 - x0), abs(y1 - y0))
            k = max(2, int(dist / step) + 1)
            for x, y in zip(np.linspace(x0, x1, k), np.linspace(y0, y1, k)):
                if minx <= x <= maxx and miny <= y <= maxy:
                    ix = min(NX - 1, int((x - minx) / (maxx - minx) * NX))
                    iy = min(NY - 1, int((y - miny) / (maxy - miny) * NY))
                    if grid[ix, iy] == 0 or (code == 5 and grid[ix, iy] == 0):
                        grid[ix, iy] = code
    print("[B] OSM 要素分布:", dict(codes))
    return grid


def build_c() -> np.ndarray:
    data = np.load(POI_COUNTS)
    cats = [str(c) for c in data["categories"]]
    stacks = np.stack([data[c] for c in cats])          # (5, NX, NY)
    total = stacks.sum(axis=0)
    code_map = {"residential": 1, "office": 2, "institution": 3, "transport": 5, "industrial": 4}
    codes = np.array([code_map[c] for c in cats])
    grid = np.zeros((NX, NY), dtype=np.int32)
    mask = total > 0
    grid[mask] = codes[stacks.argmax(axis=0)[mask]]
    return grid


def main() -> None:
    # B
    try:
        payload = fetch_osm()
        gb = rasterize_b(payload)
        np.save(OUT_B, gb)
        print("[B] 类别分布:", dict(zip(*[a.tolist() for a in np.unique(gb, return_counts=True)])))
    except Exception as exc:
        gb = None
        print("[B] 失败:", exc)

    # C
    gc = build_c()
    np.save(OUT_C, gc)
    print("[C] 类别分布:", dict(zip(*[a.tolist() for a in np.unique(gc, return_counts=True)])))

    # A
    ga = np.load(PROJECT_ROOT / "data" / "02_processed" / "landuse_map.npy")

    # 一致性（A vs B / A vs C，忽略未定类格）
    def agree(a, b):
        m = (a > 0) & (b > 0)
        if m.sum() == 0:
            return 0.0, 0
        return float((a[m] == b[m]).mean()), int(m.sum())

    ab, nab = agree(ga, gb) if gb is not None else (float("nan"), 0)
    ac, nac = agree(ga, gc)
    bc, nbc = agree(gb, gc) if gb is not None else (float("nan"), 0)
    print(f"一致性 A~B: {ab:.1%} (共判格 {nab}) | A~C: {ac:.1%} ({nac}) | B~C: {bc:.1%} ({nbc})")

    # 对比图
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import BoundaryNorm, ListedColormap

        FIG_DIR.mkdir(parents=True, exist_ok=True)
        cmap = ListedColormap(["#f0f0f0", "#e41a1c", "#377eb8", "#4daf4a", "#984ea3", "#ff7f00", "#a65628"])
        norm = BoundaryNorm(np.arange(-0.5, 7.5, 1.0), cmap.N)
        panels = [("A building+road", ga), ("B OSM Overpass", gb), ("C POI inferred", gc)]
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        for ax, (title, g) in zip(axes, panels):
            if g is None:
                ax.set_title(title + " (failed)")
                continue
            im = ax.imshow(g.T, origin="lower", cmap=cmap, norm=norm, extent=[0, NX, 0, NY])
            ax.set_title(title)
        fig.colorbar(im, ax=axes, ticks=range(7), shrink=0.8)
        fig.savefig(FIG, dpi=110, bbox_inches="tight")
        print("[图]", FIG)
    except Exception as exc:
        print("[警告] 图失败:", exc)

    stats = {
        "agree_A_B": ab, "agree_A_C": ac, "agree_B_C": bc,
        "n_A_B": nab, "n_A_C": nac, "n_B_C": nbc,
    }
    (FIG_DIR / "landuse_crossval_stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
