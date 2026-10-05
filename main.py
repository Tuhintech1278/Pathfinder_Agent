"""main.py - runs every algorithm on every maze, records metrics, saves logs + images.

Usage (from inside the project folder):
    python main.py                 run full benchmark -> results/ folder
    python main.py --live          also open a live animation window of A*
    python main.py --gif           also save an animated GIF of A* searching
"""
import argparse
import csv
import json
import os
from datetime import datetime

import matplotlib
if "--live" not in __import__("sys").argv:
    matplotlib.use("Agg")           # no window needed, just save files
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.animation import FuncAnimation, PillowWriter

from grid import random_obstacle_grid, perfect_maze
from algorithms import ALGORITHMS, a_star, manhattan

SIZE = 25
SCENARIOS = {
    "Open 10% walls": lambda: random_obstacle_grid(SIZE, SIZE, 0.10, seed=1),
    "Scattered 25% walls": lambda: random_obstacle_grid(SIZE, SIZE, 0.25, seed=2),
    "Dense 35% walls": lambda: random_obstacle_grid(SIZE, SIZE, 0.35, seed=3),
    "Twisty maze": lambda: perfect_maze(SIZE, SIZE, seed=4),
}
CMAP = ListedColormap(["white", "#2b2b2b", "#bfe3ff"])  # free, wall, explored


def draw(ax, grid, start, goal, res, title):
    rows, cols = len(grid), len(grid[0])
    img = [row[:] for row in grid]
    for (r, c) in res["expanded_order"]:
        if img[r][c] == 0:
            img[r][c] = 2
    ax.imshow(img, cmap=CMAP, vmin=0, vmax=2)
    if res["path"]:
        ax.plot([p[1] for p in res["path"]], [p[0] for p in res["path"]],
                color="red", linewidth=2)
    ax.scatter([start[1]], [start[0]], c="green", s=60, zorder=3)
    ax.scatter([goal[1]], [goal[0]], c="gold", edgecolors="black", s=80, zorder=3)
    ax.set_xticks([]); ax.set_yticks([])
    s = res["steps"] if res["steps"] is not None else "FAILED"
    ax.set_title(f"{title}\nsteps={s}  expanded={res['expanded']}  "
                 f"{res['runtime_ms']:.1f} ms", fontsize=8)


def run_benchmark(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows_out, mazes = [], {}
    for sc_name, builder in SCENARIOS.items():
        grid, start, goal = builder()
        free = sum(row.count(0) for row in grid)
        fig, axes = plt.subplots(1, len(ALGORITHMS), figsize=(4 * len(ALGORITHMS), 4.4))
        print(f"\n== {sc_name} ({free} free cells) ==")
        for ax, (alg_name, fn) in zip(axes, ALGORITHMS.items()):
            res = fn(grid, start, goal)
            draw(ax, grid, start, goal, res, alg_name)
            density = res["expanded"] / free * 100
            row = {"scenario": sc_name, "algorithm": alg_name,
                   "steps": res["steps"], "runtime_ms": round(res["runtime_ms"], 3),
                   "nodes_expanded": res["expanded"],
                   "expanded_density_pct": round(density, 1),
                   "success": bool(res["path"])}
            rows_out.append(row)
            print(f"  {alg_name:16s} steps={str(res['steps']):>5}  "
                  f"expanded={res['expanded']:>4} ({density:5.1f}%)  "
                  f"{res['runtime_ms']:8.2f} ms")
        fig.suptitle(sc_name, fontweight="bold")
        fig.tight_layout()
        fname = sc_name.replace(" ", "_").replace("%", "pct") + ".png"
        fig.savefig(os.path.join(out_dir, fname), dpi=110)
        plt.close(fig)
        mazes[sc_name] = (grid, start, goal)

    # --- CSV + JSON logs ---
    with open(os.path.join(out_dir, "metrics.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows_out[0].keys())
        w.writeheader(); w.writerows(rows_out)
    with open(os.path.join(out_dir, "metrics.json"), "w") as f:
        json.dump({"generated": datetime.now().isoformat(timespec="seconds"),
                   "grid_size": SIZE, "results": rows_out}, f, indent=2)

    # --- summary chart ---
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    keys = [("steps", "Path length (steps)"),
            ("nodes_expanded", "Nodes expanded"),
            ("runtime_ms", "Runtime (ms)")]
    scen = list(SCENARIOS)
    algs = list(ALGORITHMS)
    width = 0.8 / len(algs)
    for ax, (k, label) in zip(axes, keys):
        for i, a in enumerate(algs):
            vals = [next(r[k] or 0 for r in rows_out
                         if r["scenario"] == s and r["algorithm"] == a) for s in scen]
            ax.bar([x + i * width for x in range(len(scen))], vals, width, label=a)
        ax.set_xticks([x + 0.4 - width / 2 for x in range(len(scen))])
        ax.set_xticklabels(scen, rotation=20, fontsize=7)
        ax.set_title(label)
    axes[0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(out_dir, "summary_chart.png"), dpi=110)
    plt.close(fig)
    return mazes


def animate(grid, start, goal, live, gif_path):
    res = a_star(grid, start, goal, manhattan)
    order, path = res["expanded_order"], res["path"]
    fig, ax = plt.subplots(figsize=(6, 6))
    per_frame = max(1, len(order) // 120)
    frames = len(order) // per_frame + 15

    def update(i):
        ax.clear()
        img = [row[:] for row in grid]
        for (r, c) in order[: i * per_frame]:
            if img[r][c] == 0:
                img[r][c] = 2
        ax.imshow(img, cmap=CMAP, vmin=0, vmax=2)
        if i * per_frame >= len(order) and path:
            ax.plot([p[1] for p in path], [p[0] for p in path], "r-", linewidth=3)
        ax.scatter([start[1]], [start[0]], c="green", s=80)
        ax.scatter([goal[1]], [goal[0]], c="gold", edgecolors="k", s=100)
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"A* searching... expanded {min(i * per_frame, len(order))}")

    anim = FuncAnimation(fig, update, frames=frames, interval=60, repeat=False)
    if gif_path:
        anim.save(gif_path, writer=PillowWriter(fps=15))
        print("Saved animation:", gif_path)
    if live:
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="open live A* animation window")
    ap.add_argument("--gif", action="store_true", help="save A* animation as GIF")
    args = ap.parse_args()
    out = "results"
    mazes = run_benchmark(out)
    print(f"\nDone. Open the '{out}' folder for PNG images, metrics.csv and metrics.json")
    if args.live or args.gif:
        g, s, e = mazes["Twisty maze"]
        animate(g, s, e, args.live, os.path.join(out, "astar_search.gif") if args.gif else None)
