"""
Experiment 1: Temporal Adaptability

Core question: Does the same OD pair produce different paths at different departure times?

Design:
- Fixed OD: SW corner -> NE corner
- 4 departure times: t in {8, 12, 18, 22}
- Algorithm: TD-RiskA* (full risk)
- Weight: default preset

Expected:
- 08:00: Avoid transport POI hotspots (commute)
- 12:00: Avoid institution POI areas (school/hospital)
- 18:00: Avoid office->residential commute corridors
- 22:00: Strongly avoid residential areas (night noise penalty x10)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

EXP_DIR = Path(__file__).resolve().parent
if str(EXP_DIR) not in sys.path:
    sys.path.insert(0, str(EXP_DIR))

from scenario_builder import (
    load_micro_scenario, build_env_tensor, build_planner_config,
    get_primary_od, extract_metrics, extract_path_along_metric,
)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from methods.spatiotemporal_heterogeneity.src.algorithms.a_star.astar_4d import AStar4D

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


TIME_SLOTS = [8, 12, 18, 22]
TIME_LABELS = {8: "08:00 (Morning Rush)", 12: "12:00 (Noon)", 18: "18:00 (Evening Rush)", 22: "22:00 (Night)"}
TIME_COLORS = {8: "#E74C3C", 12: "#F39C12", 18: "#3498DB", 22: "#8E44AD"}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "EXP1-output" / "exp1_temporal"


def run_experiment():
    print("=" * 60)
    print("Experiment 1: Temporal Adaptability")
    print("=" * 60)

    print("\n[1/4] Loading micro scenario...")
    scenario = load_micro_scenario()
    print("  Grid: {}".format(scenario.grid.shape))

    print("\n[2/4] Building risk tensors...")
    env_tensor = build_env_tensor(scenario)
    print(env_tensor.summary())

    start, goal = get_primary_od(scenario.grid)
    print("\n[3/4] OD pair: start={}, goal={}".format(start, goal))

    print("\n[4/4] Running TD-RiskA* (4 time slots)...")
    results = {}
    all_metrics = []

    for t_start in TIME_SLOTS:
        label = TIME_LABELS[t_start]
        print("\n  --- {} ---".format(label))

        config = build_planner_config("default")
        planner = AStar4D(scenario.grid, env_tensor, config)

        start_with_t = (start[0], start[1], start[2], t_start)
        result = planner.search(start_with_t, goal)

        metrics = extract_metrics(result)
        metrics["t_start"] = t_start
        metrics["label"] = label
        all_metrics.append(metrics)
        results[t_start] = result

        print("    Status: {}".format(metrics["status"]))
        if metrics["status"] == "success":
            print("    Path length: {:.1f} m".format(metrics["path_length"]))
            print("    Survival: {:.6f}".format(metrics["final_survival"]))
            print("    Cum noise: {:.6f}".format(metrics["cum_noise"]))
            print("    Cum fatality: {:.8f}".format(metrics["cum_fatality"]))
            print("    Objective: {:.6f}".format(metrics["objective_cost"]))
            print("    Runtime: {:.1f} ms".format(metrics["runtime_ms"]))
            print("    Nodes: {}".format(metrics["nodes_explored"]))
        else:
            print("    Reason: {}".format(metrics.get("reason", "N/A")))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    _save_metrics_csv(all_metrics)
    _save_paths_json(results)

    print("\nGenerating figures...")
    _plot_paths_2d(results, scenario)
    _plot_paths_3d(results, scenario)
    _plot_paths_3d_plotly(results, scenario)
    _plot_cumulative_curves(results, scenario)
    _plot_metrics_table(all_metrics)

    print("\n[OK] Experiment 1 complete! Results saved to: {}".format(OUTPUT_DIR))
    return results, all_metrics


def _save_metrics_csv(all_metrics):
    csv_path = OUTPUT_DIR / "metrics.csv"
    header = "t_start,label,status,path_length,final_survival,cum_fatality,cum_property,cum_noise,objective_cost,runtime_ms,nodes_explored"
    lines = [header]
    for m in all_metrics:
        lines.append(
            "{},{},{},{:.4f},{:.6f},{:.8f},{:.8f},{:.6f},{:.6f},{:.1f},{}".format(
                m["t_start"], m["label"], m["status"],
                m["path_length"], m["final_survival"],
                m["cum_fatality"], m["cum_property"],
                m["cum_noise"], m["objective_cost"],
                m["runtime_ms"], m["nodes_explored"],
            )
        )
    csv_path.write_text("\n".join(lines), encoding="utf-8")
    print("  [OK] Saved: {}".format(csv_path))


def _save_paths_json(results):
    paths_data = {}
    for t_start, result in results.items():
        if result["status"] == "success":
            paths_data[str(t_start)] = {
                "coords": [step["coords"] for step in result["path"]],
                "states": [step["state"] for step in result["path"]],
            }
    json_path = OUTPUT_DIR / "paths.json"
    json_path.write_text(json.dumps(paths_data, indent=2), encoding="utf-8")
    print("  [OK] Saved: {}".format(json_path))


def _plot_paths_2d(results, scenario):
    fig, ax = plt.subplots(figsize=(10, 10), facecolor="white")

    bh = scenario.building_heights
    im = ax.imshow(bh, cmap="YlOrRd", origin="lower", alpha=0.6, interpolation="bilinear")
    plt.colorbar(im, ax=ax, shrink=0.7, label="Building Height (layers)")

    for t_start in TIME_SLOTS:
        result = results.get(t_start)
        if result is None or result["status"] != "success":
            continue
        path = result["path"]
        xs = [step["coords"][0] for step in path]
        ys = [step["coords"][1] for step in path]
        color = TIME_COLORS[t_start]
        label = TIME_LABELS[t_start]
        ax.plot(xs, ys, color=color, linewidth=2.5, label=label, alpha=0.9)
        ax.scatter(xs[0], ys[0], color=color, s=100, marker="o", edgecolors="black", zorder=5)
        ax.scatter(xs[-1], ys[-1], color=color, s=100, marker="*", edgecolors="black", zorder=5)

    ax.set_xlabel("X (grid cells)", fontsize=12)
    ax.set_ylabel("Y (grid cells)", fontsize=12)
    ax.set_title("Exp1: Paths at Different Departure Times", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_paths_2d.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_paths_2d.png")


def _draw_building_cube(ax, x, y, z_bottom, z_top, color, alpha=0.85):
    """Draw a single 3D building block (cube)."""
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    dx, dy = 0.4, 0.4  # half-width
    verts = [
        [x - dx, y - dy, z_bottom], [x + dx, y - dy, z_bottom],
        [x + dx, y + dy, z_bottom], [x - dx, y + dy, z_bottom],
        [x - dx, y - dy, z_top],    [x + dx, y - dy, z_top],
        [x + dx, y + dy, z_top],    [x - dx, y + dy, z_top],
    ]
    faces = [
        [verts[0], verts[1], verts[5], verts[4]],  # front
        [verts[2], verts[3], verts[7], verts[6]],  # back
        [verts[0], verts[3], verts[7], verts[4]],  # left
        [verts[1], verts[2], verts[6], verts[5]],  # right
        [verts[4], verts[5], verts[6], verts[7]],  # top
        [verts[0], verts[1], verts[2], verts[3]],  # bottom
    ]
    for i, face in enumerate(faces):
        fc = _lighten_color(color, 0.2) if i == 4 else color
        poly = Poly3DCollection([face], alpha=alpha)
        poly.set_facecolor(fc)
        poly.set_edgecolor("black")
        poly.set_linewidth(0.3)
        ax.add_collection3d(poly)


def _lighten_color(color, amount=0.3):
    """Lighten a color by a given amount."""
    import matplotlib.colors as mc
    try:
        rgb = mc.to_rgb(color)
    except Exception:
        rgb = (0.5, 0.5, 0.5)
    return tuple(min(1, c + amount * (1 - c)) for c in rgb)


def _get_building_color(height):
    """Return color based on building height (layers)."""
    if height <= 10:
        return "#90EE90"   # low-rise
    elif height <= 30:
        return "#FFD700"   # mid-rise
    elif height <= 60:
        return "#FF6347"   # high-rise
    else:
        return "#8B0000"   # skyscraper


def _plot_paths_3d(results, scenario):
    """3D path visualization with building block basemap."""
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — registers 3D projection

    fig = plt.figure(figsize=(14, 10), facecolor="white")
    ax = fig.add_subplot(111, projection="3d", computed_zorder=False)

    bh = scenario.building_heights  # (ny, nx)
    ny, nx = bh.shape
    max_h = float(bh.max())

    # --- 3D building blocks ---
    for y in range(ny):
        for x in range(nx):
            h = bh[y, x]
            if h > 0.5:
                color = _get_building_color(h)
                _draw_building_cube(ax, x, y, 0, h, color, alpha=0.85)

    # --- Ground surface ---
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    ground_verts = [[(0, 0, 0), (nx, 0, 0), (nx, ny, 0), (0, ny, 0)]]
    ground_poly = Poly3DCollection(ground_verts, alpha=0.15)
    ground_poly.set_facecolor("#D3D3D3")
    ground_poly.set_edgecolor("gray")
    ax.add_collection3d(ground_poly)

    # --- Paths ---
    for t_start in TIME_SLOTS:
        result = results.get(t_start)
        if result is None or result["status"] != "success":
            continue
        path = result["path"]
        xs = [step["coords"][0] for step in path]
        ys = [step["coords"][1] for step in path]
        zs = [step["coords"][2] for step in path]
        color = TIME_COLORS[t_start]
        label = TIME_LABELS[t_start]
        ax.plot(xs, ys, zs, color=color, linewidth=2.5, label=label, alpha=0.95, zorder=20)
        ax.scatter(xs[0], ys[0], zs[0], color=color, s=100, marker="o", edgecolors="black", zorder=25)
        ax.scatter(xs[-1], ys[-1], zs[-1], color=color, s=100, marker="*", edgecolors="black", zorder=25)

    # --- Legend for building heights ---
    from matplotlib.patches import Patch
    legend_buildings = [
        Patch(facecolor="#90EE90", edgecolor="black", label="Low-rise (1-10)"),
        Patch(facecolor="#FFD700", edgecolor="black", label="Mid-rise (10-30)"),
        Patch(facecolor="#FF6347", edgecolor="black", label="High-rise (30-60)"),
    ]
    legend1 = ax.legend(
        handles=legend_buildings, loc="lower left", fontsize=7,
        framealpha=0.9, title="Building Height", title_fontsize=8,
    )
    ax.add_artist(legend1)

    # --- Legend for paths ---
    from matplotlib.lines import Line2D
    path_handles = []
    for t_start in TIME_SLOTS:
        if results.get(t_start) and results[t_start]["status"] == "success":
            path_handles.append(
                Line2D([0], [0], color=TIME_COLORS[t_start], linewidth=2.5, label=TIME_LABELS[t_start])
            )
    if path_handles:
        legend2 = ax.legend(handles=path_handles, loc="upper left", fontsize=8, framealpha=0.9)
        ax.add_artist(legend2)

    ax.set_xlabel("X (grid cells)", fontsize=11, labelpad=8)
    ax.set_ylabel("Y (grid cells)", fontsize=11, labelpad=8)
    ax.set_zlabel("Z (altitude layers)", fontsize=11, labelpad=8)
    ax.set_title("Exp1: 3D Paths at Different Departure Times", fontsize=14, fontweight="bold", pad=15)

    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)
    ax.set_zlim(0, max_h * 1.15)
    ax.view_init(elev=30, azim=-55)

    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_paths_3d.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_paths_3d.png")


def _plot_cumulative_curves(results, scenario):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), facecolor="white")

    metrics_to_plot = [
        ("p_survival", "Survival Probability", axes[0, 0]),
        ("cum_noise", "Cumulative Noise Cost", axes[0, 1]),
        ("cum_fatality", "Cumulative Expected Fatality", axes[1, 0]),
        ("cumulative_hazard", "Cumulative Hazard Rate H", axes[1, 1]),
    ]

    for metric_key, title, ax in metrics_to_plot:
        for t_start in TIME_SLOTS:
            result = results.get(t_start)
            if result is None or result["status"] != "success":
                continue
            distances, values = extract_path_along_metric(result, metric_key)
            color = TIME_COLORS[t_start]
            label = TIME_LABELS[t_start]
            ax.plot(distances, values, color=color, linewidth=2, label=label)

        ax.set_xlabel("Cumulative Distance (m)", fontsize=10)
        ax.set_ylabel(title, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    fig.suptitle("Exp1: Cumulative Metrics Along Path", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_cumulative_curves.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_cumulative_curves.png")


def _plot_metrics_table(all_metrics):
    fig, ax = plt.subplots(figsize=(12, 4), facecolor="white")
    ax.axis("off")

    headers = ["Time", "Path(m)", "Survival", "Fatality", "Noise", "Runtime(ms)"]
    rows = []
    for m in all_metrics:
        rows.append([
            m["label"],
            "{:.1f}".format(m["path_length"]) if m["status"] == "success" else "N/A",
            "{:.6f}".format(m["final_survival"]) if m["status"] == "success" else "N/A",
            "{:.8f}".format(m["cum_fatality"]) if m["status"] == "success" else "N/A",
            "{:.4f}".format(m["cum_noise"]) if m["status"] == "success" else "N/A",
            "{:.1f}".format(m["runtime_ms"]),
        ])

    table = ax.table(cellText=rows, colLabels=headers, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.5)

    for j in range(len(headers)):
        table[0, j].set_facecolor("#3498DB")
        table[0, j].set_text_props(color="white", fontweight="bold")

    for i in range(len(rows)):
        for j in range(len(headers)):
            if i % 2 == 0:
                table[i + 1, j].set_facecolor("#ECF0F1")

    ax.set_title("Exp1: Temporal Adaptability - Metrics", fontsize=13, fontweight="bold", pad=20)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "fig_metrics_table.png", dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  [OK] Saved: fig_metrics_table.png")


def _plot_paths_3d_plotly(results, scenario):
    """Interactive 3D path visualization with building blocks (Plotly HTML)."""
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("  [SKIP] plotly not installed, skipping interactive 3D plot")
        return

    bh = scenario.building_heights  # (ny, nx)
    ny, nx = bh.shape

    all_x, all_y, all_z = [], [], []
    all_i, all_j, all_k = [], [], []
    all_intensities = []
    vertex_offset = 0

    for y in range(ny):
        for x in range(nx):
            h = bh[y, x]
            if h > 0.5:
                dx, dy = 0.4, 0.4
                verts = [
                    [x - dx, y - dy, 0], [x + dx, y - dy, 0],
                    [x + dx, y + dy, 0], [x - dx, y + dy, 0],
                    [x - dx, y - dy, h], [x + dx, y - dy, h],
                    [x + dx, y + dy, h], [x - dx, y + dy, h],
                ]
                for v in verts:
                    all_x.append(v[0]); all_y.append(v[1]); all_z.append(v[2])
                    all_intensities.append(h)
                faces = [
                    (0,1,2), (0,2,3), (4,5,6), (4,6,7),
                    (0,1,5), (0,5,4), (2,3,7), (2,7,6),
                    (0,3,7), (0,7,4), (1,2,6), (1,6,5),
                ]
                for f in faces:
                    all_i.append(f[0] + vertex_offset)
                    all_j.append(f[1] + vertex_offset)
                    all_k.append(f[2] + vertex_offset)
                vertex_offset += 8

    fig = go.Figure()

    # --- Building blocks ---
    if all_x:
        fig.add_trace(go.Mesh3d(
            x=all_x, y=all_y, z=all_z,
            i=all_i, j=all_j, k=all_k,
            intensity=all_intensities,
            colorscale=[
                [0, '#90EE90'], [0.15, '#90EE90'],
                [0.15, '#FFD700'], [0.4, '#FFD700'],
                [0.4, '#FF6347'], [0.7, '#FF6347'],
                [0.7, '#8B0000'], [1.0, '#8B0000'],
            ],
            opacity=0.9, flatshading=True,
            lighting=dict(ambient=0.7, diffuse=0.8, specular=0.2, roughness=0.5),
            colorbar=dict(title='Building Height (layers)', tickvals=[5, 20, 45, 80],
                          ticktext=['Low', 'Mid', 'High', 'Skyscraper']),
            hovertemplate='X: %{x:.0f}<br>Y: %{y:.0f}<br>Height: %{z:.0f} layers<extra></extra>',
            name='Buildings',
        ))

    # --- Paths ---
    for t_start in TIME_SLOTS:
        result = results.get(t_start)
        if result is None or result["status"] != "success":
            continue
        path = result["path"]
        xs = [step["coords"][0] for step in path]
        ys = [step["coords"][1] for step in path]
        zs = [step["coords"][2] for step in path]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode='lines+markers',
            line=dict(color=TIME_COLORS[t_start], width=6),
            marker=dict(
                size=4,
                color=TIME_COLORS[t_start],
                symbol='circle',
            ),
            name=TIME_LABELS[t_start],
            hovertemplate=(
                f'{TIME_LABELS[t_start]}<br>'
                'X: %{x:.0f}<br>Y: %{y:.0f}<br>Z: %{z:.0f}<extra></extra>'
            ),
        ))
        # Start marker
        fig.add_trace(go.Scatter3d(
            x=[xs[0]], y=[ys[0]], z=[zs[0]],
            mode='markers',
            marker=dict(size=10, color=TIME_COLORS[t_start], symbol='circle',
                        line=dict(width=2, color='black')),
            name=f'{TIME_LABELS[t_start]} Start',
            showlegend=False,
            hovertemplate=f'{TIME_LABELS[t_start]} Start<extra></extra>',
        ))
        # Goal marker
        fig.add_trace(go.Scatter3d(
            x=[xs[-1]], y=[ys[-1]], z=[zs[-1]],
            mode='markers',
            marker=dict(size=10, color=TIME_COLORS[t_start], symbol='diamond',
                        line=dict(width=2, color='black')),
            name=f'{TIME_LABELS[t_start]} Goal',
            showlegend=False,
            hovertemplate=f'{TIME_LABELS[t_start]} Goal<extra></extra>',
        ))

    fig.update_layout(
        title=dict(
            text='Exp1: 3D Paths at Different Departure Times (Interactive)',
            x=0.5, font=dict(size=18),
        ),
        scene=dict(
            xaxis_title='X (grid cells)',
            yaxis_title='Y (grid cells)',
            zaxis_title='Z (altitude layers)',
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.7),
            camera=dict(eye=dict(x=1.8, y=1.8, z=1.2)),
            xaxis=dict(range=[-1, nx]),
            yaxis=dict(range=[-1, ny]),
            zaxis=dict(range=[0, float(bh.max()) * 1.1]),
        ),
        width=1200, height=900,
        margin=dict(l=0, r=0, b=0, t=80),
        legend=dict(font=dict(size=12), y=0.98),
    )

    html_path = OUTPUT_DIR / "fig_paths_3d_interactive.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn")
    print("  [OK] Saved: fig_paths_3d_interactive.html")


if __name__ == "__main__":
    run_experiment()
