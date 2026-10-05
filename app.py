"""app.py - INTERACTIVE Pathfinding Agent  (dark neon edition)

Click to choose the START and the DESTINATION (and draw walls), pick an
algorithm, press RUN and watch the agent search: the explored area glows from
purple to cyan in the order it was visited, then a little agent runs along the
final route leaving a glowing pink trail.

Run with:   python app.py
Needs only Python (tkinter is built in). 'Compare ALL' also uses matplotlib.
"""
import csv
import json
import os
import random
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

from grid import perfect_maze
from algorithms import ALGORITHMS

# ---------------------------------------------------------------- theme
BG, PANEL, CARD = "#0d1020", "#151932", "#1f2547"
TEXT, MUTED = "#e8ebff", "#8b93c7"
ACCENT, CYAN, PINK = "#7c5cff", "#22d3ee", "#ff4d8d"
GREEN, GOLD = "#2ee59d", "#ffb703"
FREE, FREE_LINE = "#1a1f3d", "#242a52"
WALL, WALL_LINE = "#5a6599", "#8391c9"
PURPLE = "#8b3dff"

CELL = 27


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    a, b = hex_to_rgb(c1), hex_to_rgb(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


GRADIENT = [lerp_color(PURPLE, CYAN, i / 63) for i in range(64)]


class PathfinderApp:
    def __init__(self, root, rows=18, cols=30):
        self.root = root
        root.title("PathFinder AI  -  Heuristic Search Agent")
        root.configure(bg=BG)
        self.rows, self.cols = rows, cols
        self.grid = [[0] * cols for _ in range(rows)]
        self.start, self.goal = (2, 2), (rows - 3, cols - 3)
        self.anim_job = None
        self.overlay = False          # is a search drawing currently on screen?
        self.history = []             # every run is logged here

        self.mode = tk.StringVar(value="start")
        self.alg = tk.StringVar(value="A* (Manhattan)")
        self.speed = tk.IntVar(value=6)
        self.density = tk.DoubleVar(value=0.25)
        self.status = tk.StringVar(value="Click a square on the board to place the START.")
        self.stat = {k: tk.StringVar(value="-") for k in ("steps", "expanded", "density", "runtime")}

        self._build_ui()
        self._create_cells()
        self.paint_base()
        self.draw_markers()

    # ------------------------------------------------------------ widgets
    def _label(self, parent, text, **kw):
        kw.setdefault("bg", parent["bg"]); kw.setdefault("fg", TEXT)
        return tk.Label(parent, text=text, **kw)

    def _section(self, parent, text):
        self._label(parent, text.upper(), fg=MUTED, font=("Segoe UI", 8, "bold")
                    ).pack(anchor="w", pady=(12, 3))

    def _toggles(self, parent, var, items, command=None):
        f = tk.Frame(parent, bg=PANEL)
        for i, (text, val) in enumerate(items):
            tk.Radiobutton(f, text=text, variable=var, value=val, command=command,
                           indicatoron=0, bg=CARD, fg=TEXT, selectcolor=ACCENT,
                           activebackground=ACCENT, activeforeground="white",
                           relief="flat", bd=0, font=("Segoe UI", 9), pady=6, width=12,
                           cursor="hand2").grid(row=i // 2, column=i % 2, padx=2, pady=2, sticky="ew")
        f.pack(fill="x")

    def _button(self, parent, text, cmd, bg, big=False):
        hover = lerp_color(bg, "#ffffff", 0.2)
        b = tk.Button(parent, text=text, command=cmd, bg=bg, fg="white", bd=0, relief="flat",
                      activebackground=hover, activeforeground="white", cursor="hand2",
                      font=("Segoe UI", 12 if big else 9, "bold"), pady=9 if big else 5)
        b.bind("<Enter>", lambda e: b.config(bg=hover))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        b.pack(fill="x", pady=2)
        return b

    def _slider(self, parent, var, lo, hi, res):
        tk.Scale(parent, from_=lo, to=hi, resolution=res, orient="horizontal", variable=var,
                 showvalue=0, bg=PANEL, troughcolor=CARD, highlightthickness=0, bd=0,
                 activebackground=CYAN, sliderrelief="flat", length=200).pack(anchor="w")

    def _build_ui(self):
        # ----- header
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=18, pady=(12, 4))
        self._label(head, "PATH", fg=CYAN, font=("Segoe UI", 22, "bold")).pack(side="left")
        self._label(head, "FINDER AI", fg=TEXT, font=("Segoe UI", 22, "bold")).pack(side="left")
        self._label(head, "   heuristic graph search agent  |  A*  |  Dijkstra  |  Q-Learning",
                    fg=MUTED, font=("Segoe UI", 10)).pack(side="left", pady=(10, 0))

        body = tk.Frame(self.root, bg=BG)
        body.pack(padx=18, pady=(4, 14))

        # ----- left control panel
        panel = tk.Frame(body, bg=PANEL, padx=14, pady=6)
        panel.pack(side="left", fill="y", padx=(0, 14))

        self._section(panel, "1 · Click mode")
        self._toggles(panel, self.mode, [("●  Start", "start"), ("◆  Destination", "goal"),
                                         ("■  Draw walls", "wall"), ("□  Erase", "erase")],
                      command=self.on_mode_change)
        self._section(panel, "2 · Agent")
        self._toggles(panel, self.alg, [("Dijkstra", "Dijkstra"), ("A*  Manhattan", "A* (Manhattan)"),
                                        ("A*  Euclidean", "A* (Euclidean)"), ("Q-Learning", "Q-Learning")])
        self._section(panel, "3 · Animation speed")
        self._slider(panel, self.speed, 1, 30, 1)

        tk.Frame(panel, height=8, bg=PANEL).pack()
        self._button(panel, "▶   RUN AGENT", self.run, ACCENT, big=True)
        self._button(panel, "Compare ALL agents", self.compare_all, "#0e8fa8")
        self._button(panel, "Clear path", self.clear_path, "#3a4180")

        self._section(panel, "Maze tools")
        self._label(panel, "wall density", fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self._slider(panel, self.density, 0.05, 0.40, 0.01)
        self._button(panel, "Random walls", self.random_walls, "#3a4180")
        self._button(panel, "Twisty maze", self.make_maze, "#3a4180")
        self._button(panel, "Clear everything", self.clear_all, "#6b2a4a")
        self._button(panel, "Export run log (CSV + JSON)", self.export_log, "#1f8f63")

        # ----- right side: board, legend, stat cards
        right = tk.Frame(body, bg=BG)
        right.pack(side="left")

        self.canvas = tk.Canvas(right, width=self.cols * CELL, height=self.rows * CELL, bg=BG,
                                highlightthickness=2, highlightbackground="#2a3066")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_click)

        legend = tk.Frame(right, bg=BG)
        legend.pack(fill="x", pady=(8, 4))
        for color, text in [(GREEN, "Start"), (GOLD, "Destination"), (WALL, "Wall"),
                            (PURPLE, "Explored (early)"), (CYAN, "Explored (late)"), (PINK, "Path")]:
            tk.Label(legend, bg=color, width=2).pack(side="left", padx=(0, 4))
            self._label(legend, text, fg=MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(0, 14))

        cards = tk.Frame(right, bg=BG)
        cards.pack(fill="x", pady=4)
        for key, caption, color in [("steps", "PATH STEPS", PINK), ("expanded", "NODES EXPANDED", CYAN),
                                    ("density", "EXPANDED DENSITY", "#b79cff"), ("runtime", "RUNTIME", GOLD)]:
            card = tk.Frame(cards, bg=CARD, padx=12, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=3)
            tk.Label(card, textvariable=self.stat[key], bg=CARD, fg=color,
                     font=("Segoe UI", 20, "bold")).pack(anchor="w")
            tk.Label(card, text=caption, bg=CARD, fg=MUTED, font=("Segoe UI", 8, "bold")).pack(anchor="w")

        tk.Label(right, textvariable=self.status, bg=BG, fg=MUTED, font=("Segoe UI", 10),
                 anchor="w", justify="left", wraplength=800).pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------------ drawing
    def _create_cells(self):
        self.rects = [[self.canvas.create_rectangle(c * CELL + 1, r * CELL + 1,
                                                    (c + 1) * CELL - 1, (r + 1) * CELL - 1,
                                                    fill=FREE, outline=FREE_LINE)
                       for c in range(self.cols)] for r in range(self.rows)]

    def paint_cell(self, r, c):
        if self.grid[r][c] == 1:
            self.canvas.itemconfig(self.rects[r][c], fill=WALL, outline=WALL_LINE)
        else:
            self.canvas.itemconfig(self.rects[r][c], fill=FREE, outline=FREE_LINE)

    def paint_base(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.paint_cell(r, c)

    def center(self, cell):
        return cell[1] * CELL + CELL / 2, cell[0] * CELL + CELL / 2

    def draw_markers(self):
        self.canvas.delete("marker")
        x, y = self.center(self.start)
        self.canvas.create_oval(x - 11, y - 11, x + 11, y + 11, fill="", outline=GREEN, width=2, tags="marker")
        self.canvas.create_oval(x - 6, y - 6, x + 6, y + 6, fill=GREEN, outline="white", width=2, tags="marker")
        x, y = self.center(self.goal)
        self.canvas.create_polygon(x, y - 12, x + 12, y, x, y + 12, x - 12, y, fill=GOLD,
                                   outline="white", width=2, tags="marker")
        self.canvas.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#7a5200", outline="", tags="marker")
        self.canvas.tag_raise("marker")

    def clear_overlay(self):
        """Remove the search drawing and show the plain board again."""
        self.canvas.delete("path", "agent")
        if self.overlay:
            self.paint_base()
            self.overlay = False
        self.canvas.tag_raise("marker")

    # ------------------------------------------------------------ mouse
    def on_mode_change(self):
        hints = {"start": "Click a square to place the START.",
                 "goal": "Click a square to place the DESTINATION.",
                 "wall": "Click or drag to draw walls.",
                 "erase": "Click or drag to erase walls."}
        self.status.set(hints[self.mode.get()])

    def on_click(self, event):
        r, c = event.y // CELL, event.x // CELL
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return
        self.stop_animation()
        self.clear_overlay()
        cell, m = (r, c), self.mode.get()
        if m == "start" and cell != self.goal:
            self.grid[r][c] = 0
            self.start = cell
        elif m == "goal" and cell != self.start:
            self.grid[r][c] = 0
            self.goal = cell
        elif m == "wall" and cell not in (self.start, self.goal):
            self.grid[r][c] = 1
        elif m == "erase":
            self.grid[r][c] = 0
        self.paint_cell(r, c)
        self.draw_markers()

    # ------------------------------------------------------------ running
    def run(self):
        self.stop_animation()
        self.clear_overlay()
        name = self.alg.get()
        self.status.set(f"{name} is searching..." +
                        ("  (Q-Learning trains by trial and error first - give it a moment)"
                         if name == "Q-Learning" else ""))
        self.root.update_idletasks()
        res = ALGORITHMS[name](self.grid, self.start, self.goal)
        free = sum(row.count(0) for row in self.grid)
        rec = {"time": datetime.now().isoformat(timespec="seconds"), "algorithm": name,
               "start": list(self.start), "goal": list(self.goal),
               "steps": res["steps"], "nodes_expanded": res["expanded"],
               "expanded_density_pct": round(res["expanded"] / free * 100, 1),
               "runtime_ms": round(res["runtime_ms"], 3), "success": bool(res["path"])}
        self.history.append(rec)
        self.animate(res, rec)

    def animate(self, res, rec):
        order, path = res["expanded_order"], res["path"]
        per_frame = max(1, int(self.speed.get()))
        total = max(len(order), 1)
        self.overlay = True
        state = {"i": 0, "k": 0}
        points = [self.center(p) for p in path]

        def explore():
            i = state["i"]
            for j in range(i, min(i + per_frame, len(order))):
                r, c = order[j]
                col = GRADIENT[int(j / total * 63)]
                self.canvas.itemconfig(self.rects[r][c], fill=col, outline=col)
            state["i"] += per_frame
            if state["i"] < len(order):
                self.anim_job = self.root.after(15, explore)
            else:
                self.canvas.tag_raise("marker")
                self.anim_job = self.root.after(250, run_path)

        def run_path():
            if not path:
                self.finish(rec)
                return
            k = state["k"]
            self.canvas.delete("path", "agent")
            if k >= 1:
                flat = [v for p in points[:k + 1] for v in p]
                for w, col in ((14, "#4a1636"), (8, PINK), (3, "#ffd6e6")):
                    self.canvas.create_line(*flat, fill=col, width=w, capstyle="round",
                                            joinstyle="round", tags="path")
            x, y = points[k]
            self.canvas.create_oval(x - 8, y - 8, x + 8, y + 8, fill="white", outline=PINK,
                                    width=3, tags="agent")
            self.canvas.tag_raise("marker")
            self.canvas.tag_raise("agent")
            state["k"] += 1
            if state["k"] < len(points):
                self.anim_job = self.root.after(max(8, 60 - 2 * per_frame), run_path)
            else:
                self.finish(rec)

        explore()

    def finish(self, rec):
        self.anim_job = None
        if rec["success"]:
            self.stat["steps"].set(str(rec["steps"]))
            self.stat["expanded"].set(str(rec["nodes_expanded"]))
            self.stat["density"].set(f"{rec['expanded_density_pct']}%")
            self.stat["runtime"].set(f"{rec['runtime_ms']:.1f} ms")
            self.status.set(f"{rec['algorithm']} reached the destination. Try another agent on the "
                            "same board and compare the glowing area.")
        else:
            for k in self.stat:
                self.stat[k].set("-")
            self.status.set(f"{rec['algorithm']}: NO PATH FOUND - the destination is walled off "
                            "(or Q-Learning could not learn a route).")

    def stop_animation(self):
        if self.anim_job:
            self.root.after_cancel(self.anim_job)
            self.anim_job = None

    # ------------------------------------------------------------ board tools
    def clear_path(self):
        self.stop_animation()
        self.clear_overlay()
        self.status.set("Path cleared.")

    def clear_all(self):
        self.stop_animation()
        self.grid = [[0] * self.cols for _ in range(self.rows)]
        self.overlay = True
        self.clear_overlay()
        self.status.set("Board cleared.")

    def random_walls(self):
        self.stop_animation()
        d = self.density.get()
        self.grid = [[1 if random.random() < d else 0 for _ in range(self.cols)]
                     for _ in range(self.rows)]
        self.grid[self.start[0]][self.start[1]] = 0
        self.grid[self.goal[0]][self.goal[1]] = 0
        self.overlay = True
        self.clear_overlay()
        self.status.set(f"Random walls at {int(d * 100)}% - some layouts may block the goal. Press RUN!")

    def make_maze(self):
        self.stop_animation()
        g, _, _ = perfect_maze(self.rows - (self.rows % 2 == 0), self.cols - (self.cols % 2 == 0),
                               seed=random.randrange(10 ** 6))
        self.grid = [[1] * self.cols for _ in range(self.rows)]
        for r, row in enumerate(g):
            for c, v in enumerate(row):
                self.grid[r][c] = v
        free = [(r, c) for r in range(self.rows) for c in range(self.cols) if self.grid[r][c] == 0]
        self.start, self.goal = (0, 0), free[-1]
        self.overlay = True
        self.clear_overlay()
        self.draw_markers()
        self.status.set("New maze! Start and destination were reset - you can move them.")

    # ------------------------------------------------------------ export
    def export_log(self):
        if not self.history:
            messagebox.showinfo("Nothing yet", "Run the agent at least once first.")
            return
        os.makedirs("results", exist_ok=True)
        with open("results/run_log.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.history[0].keys())
            w.writeheader()
            w.writerows(self.history)
        with open("results/run_log.json", "w") as f:
            json.dump(self.history, f, indent=2)
        self.status.set("Saved  results/run_log.csv  and  results/run_log.json")

    def compare_all(self):
        """Run every agent on the CURRENT board and save a dark-themed picture."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.colors import ListedColormap
        os.makedirs("results", exist_ok=True)
        self.status.set("Comparing all agents (Q-Learning takes a few seconds)...")
        self.root.update_idletasks()
        free = sum(row.count(0) for row in self.grid)
        fig, axes = plt.subplots(1, len(ALGORITHMS), figsize=(4.4 * len(ALGORITHMS), 3.6),
                                 facecolor=BG)
        cmap = ListedColormap([FREE, WALL, "#1b9bb5"])
        for ax, (name, fn) in zip(axes, ALGORITHMS.items()):
            res = fn(self.grid, self.start, self.goal)
            img = [row[:] for row in self.grid]
            for (r, c) in res["expanded_order"]:
                if img[r][c] == 0:
                    img[r][c] = 2
            ax.imshow(img, cmap=cmap, vmin=0, vmax=2)
            if res["path"]:
                ax.plot([p[1] for p in res["path"]], [p[0] for p in res["path"]],
                        color=PINK, lw=2.5)
            ax.scatter(*self.start[::-1], c=GREEN, s=70, edgecolors="white", zorder=3)
            ax.scatter(*self.goal[::-1], c=GOLD, s=90, marker="D", edgecolors="white", zorder=3)
            ax.set_xticks([]); ax.set_yticks([])
            s = res["steps"] if res["steps"] is not None else "FAILED"
            ax.set_title(f"{name}\nsteps={s}   expanded={res['expanded']}   "
                         f"{res['runtime_ms']:.1f} ms", fontsize=9, color=TEXT)
            self.history.append({
                "time": datetime.now().isoformat(timespec="seconds"), "algorithm": name,
                "start": list(self.start), "goal": list(self.goal), "steps": res["steps"],
                "nodes_expanded": res["expanded"],
                "expanded_density_pct": round(res["expanded"] / free * 100, 1),
                "runtime_ms": round(res["runtime_ms"], 3), "success": bool(res["path"])})
        fig.tight_layout()
        fig.savefig("results/comparison.png", dpi=120, facecolor=BG)
        plt.close(fig)
        self.export_log()
        self.status.set("Saved  results/comparison.png  (+ run logs). Open the results folder.")


if __name__ == "__main__":
    root = tk.Tk()
    PathfinderApp(root)
    root.update_idletasks()
    try:   # centre the window on screen
        w, h = root.winfo_width(), root.winfo_height()
        root.geometry(f"+{(root.winfo_screenwidth() - w) // 2}+{max((root.winfo_screenheight() - h) // 2 - 20, 0)}")
    except Exception:
        pass
    root.resizable(False, False)
    root.mainloop()
