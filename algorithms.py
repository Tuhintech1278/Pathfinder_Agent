"""algorithms.py - the search agents, written from scratch.

Every function returns a dictionary with the same keys so they can be compared:
  path            list of cells from start to goal ([] if none found)
  steps           number of moves in the path
  expanded        number of cells the agent "looked at" (fewer = smarter)
  expanded_order  the order cells were expanded (used for animations)
  runtime_ms      how long it took
"""
import heapq
import math
import random
import time

from grid import neighbors, MOVES


# ---------- heuristics (an educated guess of distance-to-goal) ----------
def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def euclidean(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def zero(a, b):
    return 0


def _rebuild(came_from, goal):
    path, cur = [], goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    return path[::-1]


# ---------- A* and Dijkstra (Dijkstra = A* with heuristic 0) ----------
def a_star(grid, start, goal, heuristic=manhattan):
    t0 = time.perf_counter()
    # heap items: (f = g + h, tie-breaker, cell). Smallest f pops first.
    counter = 0
    open_heap = [(heuristic(start, goal), counter, start)]
    g = {start: 0}              # cheapest known cost from start to each cell
    came_from = {start: None}   # breadcrumbs to rebuild the path
    closed, order = set(), []

    while open_heap:
        _, _, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue            # stale duplicate entry
        closed.add(cur)
        order.append(cur)
        if cur == goal:
            path = _rebuild(came_from, goal)
            return _result(path, order, t0)
        for nxt in neighbors(grid, cur):
            new_g = g[cur] + 1
            if nxt not in g or new_g < g[nxt]:
                g[nxt] = new_g
                came_from[nxt] = cur
                counter += 1
                heapq.heappush(open_heap, (new_g + heuristic(nxt, goal), counter, nxt))
    return _result([], order, t0)


def dijkstra(grid, start, goal):
    return a_star(grid, start, goal, heuristic=zero)


def _result(path, order, t0, extra=None):
    res = {
        "path": path,
        "steps": max(len(path) - 1, 0) if path else None,
        "expanded": len(order),
        "expanded_order": order,
        "runtime_ms": (time.perf_counter() - t0) * 1000,
    }
    if extra:
        res.update(extra)
    return res


# ---------- Q-Learning (the agent LEARNS by trial and error) ----------
def q_learning(grid, start, goal, episodes=1500, alpha=0.5, gamma=0.95,
               eps_start=1.0, eps_end=0.05, seed=0):
    """Tabular Q-learning.
    Q[state][action] = how good is taking `action` in `state`.
    Update rule:  Q += alpha * (reward + gamma * max(Q[next]) - Q)
    Rewards: -1 per step, -5 for bumping a wall, +100 for reaching the goal."""
    t0 = time.perf_counter()
    rng = random.Random(seed)
    rows, cols = len(grid), len(grid[0])
    Q = [[0.0] * 4 for _ in range(rows * cols)]
    visited = set()
    max_steps = rows * cols * 2
    updates = 0

    def step(cell, a):
        dr, dc = MOVES[a]
        nr, nc = cell[0] + dr, cell[1] + dc
        if not (0 <= nr < rows and 0 <= nc < cols) or grid[nr][nc] == 1:
            return cell, -5.0, False          # bumped into wall / edge
        if (nr, nc) == goal:
            return (nr, nc), 100.0, True
        return (nr, nc), -1.0, False

    for ep in range(episodes):
        eps = eps_end + (eps_start - eps_end) * (1 - ep / episodes)
        cell = start
        for _ in range(max_steps):
            visited.add(cell)
            s = cell[0] * cols + cell[1]
            if rng.random() < eps:
                a = rng.randrange(4)           # explore
            else:
                best = max(Q[s])               # exploit (random tie-break)
                a = rng.choice([i for i in range(4) if Q[s][i] == best])
            nxt, reward, done = step(cell, a)
            s2 = nxt[0] * cols + nxt[1]
            target = reward + (0 if done else gamma * max(Q[s2]))
            Q[s][a] += alpha * (target - Q[s][a])
            updates += 1
            cell = nxt
            if done:
                break

    # Follow the learned policy greedily to extract the path
    path, cell, seen = [start], start, {start}
    for _ in range(rows * cols):
        if cell == goal:
            break
        s = cell[0] * cols + cell[1]
        a = max(range(4), key=lambda i: Q[s][i])
        cell, _, _ = step(cell, a)
        if cell in seen:                       # looping -> policy failed
            path = []
            break
        seen.add(cell)
        path.append(cell)
    if path and path[-1] != goal:
        path = []
    order = sorted(visited)
    return _result(path, order, t0, {"training_updates": updates})


ALGORITHMS = {
    "Dijkstra": dijkstra,
    "A* (Manhattan)": lambda g, s, e: a_star(g, s, e, manhattan),
    "A* (Euclidean)": lambda g, s, e: a_star(g, s, e, euclidean),
    "Q-Learning": q_learning,
}
