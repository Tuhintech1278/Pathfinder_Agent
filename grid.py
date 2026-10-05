"""grid.py - builds the mazes (grids) the agent has to solve.

A grid is a list of rows. Each cell is:  0 = free road,  1 = wall.
Positions are (row, col) tuples. Start = top-left, Goal = bottom-right.
"""
import random
from collections import deque

MOVES = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # up, down, left, right


def neighbors(grid, cell):
    """Return the free cells the agent can step to from `cell`."""
    r, c = cell
    rows, cols = len(grid), len(grid[0])
    out = []
    for dr, dc in MOVES:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 0:
            out.append((nr, nc))
    return out


def is_solvable(grid, start, goal):
    """Quick breadth-first check: can we reach goal from start at all?"""
    seen, queue = {start}, deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            return True
        for nxt in neighbors(grid, cur):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return False


def random_obstacle_grid(rows, cols, density, seed):
    """Scatter walls randomly. density=0.25 means about 25% of cells are walls.
    Keeps trying (new random layout) until a path from start to goal exists."""
    rng = random.Random(seed)
    start, goal = (0, 0), (rows - 1, cols - 1)
    while True:
        grid = [[1 if rng.random() < density else 0 for _ in range(cols)]
                for _ in range(rows)]
        grid[start[0]][start[1]] = 0
        grid[goal[0]][goal[1]] = 0
        if is_solvable(grid, start, goal):
            return grid, start, goal


def perfect_maze(rows, cols, seed):
    """Classic twisty maze (recursive backtracker). rows/cols should be odd."""
    rng = random.Random(seed)
    rows += (rows % 2 == 0)
    cols += (cols % 2 == 0)
    grid = [[1] * cols for _ in range(rows)]
    grid[0][0] = 0
    stack = [(0, 0)]
    while stack:
        r, c = stack[-1]
        options = []
        for dr, dc in MOVES:
            nr, nc = r + 2 * dr, c + 2 * dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == 1:
                options.append((nr, nc, r + dr, c + dc))
        if options:
            nr, nc, wr, wc = rng.choice(options)
            grid[wr][wc] = 0   # knock down the wall between
            grid[nr][nc] = 0
            stack.append((nr, nc))
        else:
            stack.pop()
    return grid, (0, 0), (rows - 1, cols - 1)
