"""
Ataxx - the game rules (no graphics in this file).

RULES (that's all of them):
  - On your turn, pick one of your pieces and move it to an EMPTY square:
      * 1 square away (any direction)  = CLONE: the original stays, you gain a piece
      * 2 squares away                  = JUMP:  the original leaves its square
  - Every enemy piece touching the square you landed on becomes yours.
  - The game ends when the board is full, when a player has no pieces left, or
    when the player to move has no legal move (the other player then gets all
    the empty squares). Most pieces wins.

Course topics used in this file:
  - Matrix (2D list):        the board; validating, flipping, transposing and
                             rotating layouts; 3x3 neighbour window with bounds checks
  - Two pointers:            flipping rows and flipping the board top <-> bottom
  - Hash table (dict):       pieces per player, move targets, match wins, history entries
  - Set:                     each player's piece positions (O(1) add/remove/lookup)
  - Stack:                   undo, and a second stack for redo
  - Queue (deque):           turn order, BFS, and the replay
  - BFS on a grid:           checks a random board has no unreachable squares
  - Sorting:                 the computer ranks its moves; the scoreboard
"""

import random
from collections import deque

SIZE = 7
HALF = SIZE // 2 + 1          # 4: a quarter of the board, including the middle row/column

EMPTY = None
RED = "red"
BLUE = "blue"
BLOCK = "block"

# Starting pieces: each player owns two opposite corners.
START_PIECES = {(0, 0): RED, (SIZE - 1, SIZE - 1): RED,
                (0, SIZE - 1): BLUE, (SIZE - 1, 0): BLUE}

# The 8 squares touching a square (distance 1): used for CLONE moves and captures.
CLONE_STEPS = [(-1, -1), (-1, 0), (-1, 1),
               (0, -1),           (0, 1),
               (1, -1),  (1, 0),  (1, 1)]

# The 16 squares exactly 2 away: used for JUMP moves.
JUMP_STEPS = []
for dr in range(-2, 3):
    for dc in range(-2, 3):
        if max(abs(dr), abs(dc)) == 2:
            JUMP_STEPS.append((dr, dc))


# ======================================================================
# Matrix helpers (board layouts)
# ======================================================================

def check_square(matrix, size):
    """Raise ValueError unless matrix is size x size (the length check is
    inside the loop, before each row is used)."""
    if len(matrix) != size:
        raise ValueError(f"expected {size} rows, got {len(matrix)}")
    for r in range(len(matrix)):
        if len(matrix[r]) != size:
            raise ValueError(f"row {r} has length {len(matrix[r])}, expected {size}")


def copy_matrix(matrix):
    """A real copy. (matrix[:] would only copy the outer list, and both
    'copies' would still share the same rows.)"""
    return [row[:] for row in matrix]


def flip_row(row):
    """Return a reversed copy of a row, using two pointers."""
    result = row[:]
    left = 0
    right = len(result) - 1
    while left < right:
        result[left], result[right] = result[right], result[left]
        left += 1
        right -= 1
    return result


def flip_top_bottom(matrix):
    """Flip the rows of a matrix in place, with two pointers. O(rows)."""
    top = 0
    bottom = len(matrix) - 1
    while top < bottom:
        matrix[top], matrix[bottom] = matrix[bottom], matrix[top]
        top += 1
        bottom -= 1
    return matrix


def transpose(matrix):
    """Rows become columns: result[c][r] = matrix[r][c]."""
    rows = len(matrix)
    cols = len(matrix[0])
    result = [[None] * rows for _ in range(cols)]
    for r in range(rows):
        for c in range(cols):
            result[c][r] = matrix[r][c]
    return result


def rotate_clockwise(matrix):
    """Rotate 90 degrees clockwise = transpose, then flip every row."""
    turned = transpose(matrix)
    for r in range(len(turned)):
        turned[r] = flip_row(turned[r])
    return turned


def mirror_quarter(quarter):
    """Build a full 7x7 layout from its top-left 4x4 quarter by mirroring it
    left<->right and then top<->bottom. A mirrored board is fair: both
    players' corners look exactly the same."""
    check_square(quarter, HALF)
    top_half = []
    for row in quarter:
        row = list(row)
        top_half.append(row + flip_row(row[:HALF - 1]))   # don't repeat the middle column
    bottom_half = flip_top_bottom(copy_matrix(top_half[:HALF - 1]))   # don't repeat the middle row
    return top_half + bottom_half


# Layouts are drawn as their top-left quarter. "#" = blocked square.
QUARTERS = {
    "Open":    ["....",
                "....",
                "....",
                "...."],
    "Pillars": ["....",
                ".#..",
                "....",
                "...."],
    "Wall":    ["....",
                "...#",
                "...#",
                "...."],
    "Diamond": ["....",
                "..#.",
                ".#..",
                "...."],
}
LAYOUT_NAMES = ["Open", "Pillars", "Wall", "Wall (turned)", "Diamond", "Random"]


def reachable_squares(layout, start):
    """BFS: every non-blocked square a piece could eventually reach from start,
    moving 1 or 2 squares at a time. Queue = squares still to explore,
    set = squares already seen (so nothing is visited twice). O(cells)."""
    queue = deque([start])
    seen = {start}
    while queue:
        r, c = queue.popleft()
        for dr, dc in CLONE_STEPS + JUMP_STEPS:
            nr, nc = r + dr, c + dc
            if (0 <= nr < SIZE and 0 <= nc < SIZE
                    and layout[nr][nc] != "#" and (nr, nc) not in seen):
                seen.add((nr, nc))
                queue.append((nr, nc))
    return seen


def is_playable(layout):
    """True if no empty square is cut off from the starting corner."""
    open_squares = sum(1 for row in layout for cell in row if cell != "#")
    return len(reachable_squares(layout, (0, 0))) == open_squares


def random_layout(rng):
    """A random, fair, playable board: random quarter -> mirror -> maybe rotate,
    and try again until BFS says every square can be reached."""
    while True:
        quarter = []
        for r in range(HALF):
            row = []
            for c in range(HALF):
                near_corner = r <= 1 and c <= 1          # keep the start corner free
                row.append("#" if (not near_corner and rng.random() < 0.18) else ".")
            quarter.append(row)
        layout = mirror_quarter(quarter)
        if rng.random() < 0.5:
            layout = rotate_clockwise(layout)
        if is_playable(layout):
            return layout


def build_layout(name, rng):
    if name == "Random":
        return random_layout(rng)
    if name == "Wall (turned)":
        return rotate_clockwise(mirror_quarter(QUARTERS["Wall"]))
    return mirror_quarter(QUARTERS[name])


# ======================================================================
# The game
# ======================================================================

class Ataxx:

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.wins = {RED: 0, BLUE: 0, "draws": 0}   # hash table, kept between games
        self.layout_index = 0
        self.new_game()

    def new_game(self, layout_name=None):
        if layout_name is None:
            layout_name = LAYOUT_NAMES[self.layout_index]
        self.layout_name = layout_name
        layout = build_layout(layout_name, self.rng)

        # The board: a 7x7 matrix holding EMPTY, BLOCK, RED or BLUE.
        self.grid = [[BLOCK if layout[r][c] == "#" else EMPTY for c in range(SIZE)]
                     for r in range(SIZE)]

        # Hash table of sets: player -> positions of their pieces.
        # Counting pieces is len(set): O(1) instead of scanning the board.
        self.pieces = {RED: set(), BLUE: set()}
        for (r, c), player in START_PIECES.items():
            self.grid[r][c] = player
            self.pieces[player].add((r, c))

        self.start_grid = copy_matrix(self.grid)   # needed for the replay
        self.turns = deque([RED, BLUE])            # queue: whoever is at the front plays
        self.undo_stack = []
        self.redo_stack = []
        self.over = False
        self.winner = None

    def next_layout(self):
        self.layout_index = (self.layout_index + 1) % len(LAYOUT_NAMES)
        self.new_game()

    # ------------------------------------------------------------------
    # Questions about the board
    # ------------------------------------------------------------------

    def current_player(self):
        return self.turns[0]

    def opponent(self, player):
        return BLUE if player == RED else RED

    def in_bounds(self, r, c):
        return 0 <= r < SIZE and 0 <= c < SIZE

    def count(self, player):
        return len(self.pieces[player])

    def empty_squares(self):
        return [(r, c) for r in range(SIZE) for c in range(SIZE) if self.grid[r][c] is EMPTY]

    def neighbours(self, r, c, who):
        """The squares in the 3x3 window around (r, c) that belong to who.
        Bounds are checked, so edges and corners just have fewer neighbours."""
        found = []
        for dr, dc in CLONE_STEPS:
            nr, nc = r + dr, c + dc
            if self.in_bounds(nr, nc) and self.grid[nr][nc] == who:
                found.append((nr, nc))
        return found

    def targets(self, r, c):
        """Hash table of where the piece on (r, c) can go: square -> "clone" or "jump"."""
        result = {}
        for steps, kind in ((CLONE_STEPS, "clone"), (JUMP_STEPS, "jump")):
            for dr, dc in steps:
                nr, nc = r + dr, c + dc
                if self.in_bounds(nr, nc) and self.grid[nr][nc] is EMPTY:
                    result[(nr, nc)] = kind
        return result

    def has_move(self, player):
        for r, c in self.pieces[player]:
            if self.targets(r, c):
                return True          # stop at the first piece that can move
        return False

    # ------------------------------------------------------------------
    # Moving
    # ------------------------------------------------------------------

    def move(self, src, dst):
        """Play src -> dst for the current player. Returns the history entry,
        or None if the move is not allowed."""
        if self.over:
            return None
        r, c = src
        if not self.in_bounds(r, c) or self.grid[r][c] != self.current_player():
            return None
        if dst not in self.targets(r, c):
            return None
        entry = self._apply(src, dst)
        self.undo_stack.append(entry)    # PUSH
        self.redo_stack.clear()          # a new move makes the old "future" invalid
        return entry

    def _apply(self, src, dst):
        player = self.current_player()
        enemy = self.opponent(player)
        kind = self.targets(*src)[dst]

        if kind == "jump":
            self.grid[src[0]][src[1]] = EMPTY
            self.pieces[player].remove(src)
        self.grid[dst[0]][dst[1]] = player
        self.pieces[player].add(dst)

        converted = self.neighbours(dst[0], dst[1], enemy)
        for r, c in converted:
            self.grid[r][c] = player
            self.pieces[enemy].remove((r, c))
            self.pieces[player].add((r, c))

        self.turns.append(self.turns.popleft())   # rotate the queue: next player

        # History entry (a dict) has everything needed to undo the move exactly.
        entry = {"player": player, "src": src, "dst": dst, "kind": kind,
                 "converted": converted, "filled": [], "ended": False}
        self._check_end(entry)
        return entry

    def _check_end(self, entry):
        mover = entry["player"]
        nxt = self.current_player()
        if self.count(nxt) > 0 and self.empty_squares() and self.has_move(nxt):
            return                          # game goes on
        if self.count(nxt) > 0 and self.empty_squares():
            # The next player is stuck: the mover gets every empty square.
            for r, c in self.empty_squares():
                self.grid[r][c] = mover
                self.pieces[mover].add((r, c))
                entry["filled"].append((r, c))
        entry["ended"] = True
        self.over = True
        if self.count(RED) > self.count(BLUE):
            self.winner = RED
        elif self.count(BLUE) > self.count(RED):
            self.winner = BLUE
        else:
            self.winner = "draw"
        self.wins[self.winner if self.winner != "draw" else "draws"] += 1

    def undo(self):
        """POP the last move and reverse every change it made."""
        if not self.undo_stack:
            return None
        entry = self.undo_stack.pop()
        self._reverse(entry)
        self.redo_stack.append(entry)
        return entry

    def _reverse(self, entry):
        player = entry["player"]
        enemy = self.opponent(player)
        if entry["ended"]:
            self.wins[self.winner if self.winner != "draw" else "draws"] -= 1
            self.over = False
            self.winner = None
        for r, c in entry["filled"]:
            self.grid[r][c] = EMPTY
            self.pieces[player].remove((r, c))
        for r, c in entry["converted"]:
            self.grid[r][c] = enemy
            self.pieces[player].remove((r, c))
            self.pieces[enemy].add((r, c))
        dr, dc = entry["dst"]
        self.grid[dr][dc] = EMPTY
        self.pieces[player].remove((dr, dc))
        if entry["kind"] == "jump":
            sr, sc = entry["src"]
            self.grid[sr][sc] = player
            self.pieces[player].add((sr, sc))
        self.turns.appendleft(self.turns.pop())   # rotate the queue backwards

    def redo(self):
        """Replay the move that was just undone."""
        if not self.redo_stack:
            return None
        entry = self.redo_stack.pop()
        new_entry = self._apply(entry["src"], entry["dst"])
        self.undo_stack.append(new_entry)
        return new_entry

    def replay_queue(self):
        """All moves of this game, oldest first (FIFO)."""
        return deque(self.undo_stack)

    # ------------------------------------------------------------------
    # Computer player (greedy)
    # ------------------------------------------------------------------

    def computer_move(self):
        """Score every legal move by how many pieces it gains, then sort.
        A clone gains 1 extra piece, so it beats a jump with the same captures.
        Ties are broken at random so games don't repeat. Returns (src, dst) or None."""
        player = self.current_player()
        enemy = self.opponent(player)
        moves = []
        for src in sorted(self.pieces[player]):
            for dst, kind in self.targets(*src).items():
                gain = len(self.neighbours(dst[0], dst[1], enemy))
                if kind == "clone":
                    gain += 1
                moves.append((gain, src, dst))
        if not moves:
            return None
        moves.sort(key=lambda m: m[0], reverse=True)   # best gain first
        best_gain = moves[0][0]
        best = [m for m in moves if m[0] == best_gain]
        _, src, dst = self.rng.choice(best)
        return src, dst

    # ------------------------------------------------------------------
    # Scoreboard
    # ------------------------------------------------------------------

    def scoreboard(self):
        ranking = sorted(self.wins.items(), key=lambda item: item[1], reverse=True)
        return "   ".join(f"{name.capitalize()}: {n}" for name, n in ranking)

    def game_stats(self):
        """Per-player totals for this game, worked out from the undo stack.
        Nothing is stored separately, so undo/redo can never make them wrong.
        O(moves played)."""
        stats = {p: {"moves": 0, "clones": 0, "jumps": 0, "captured": 0, "best": 0}
                 for p in (RED, BLUE)}
        for entry in self.undo_stack:
            s = stats[entry["player"]]
            s["moves"] += 1
            s["clones" if entry["kind"] == "clone" else "jumps"] += 1
            n = len(entry["converted"])
            s["captured"] += n
            s["best"] = max(s["best"], n)
        return stats
