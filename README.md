# Ataxx — DSA Group Project (Group 8)

A two-player strategy game on a 7×7 board, built in Python with `game2dboard`.

**Rules (all of them):**

- On your turn, move one of your pieces to an empty square.
  - **1 square away = clone.** You keep the original and gain a piece.
  - **2 squares away = jump.** The piece leaves its square.
- Every enemy piece touching the square you land on becomes yours.
- The game ends when:
  - the board is full, or
  - one player has no pieces left, or
  - the player to move is stuck (the other player then gets every empty square).
- Most pieces wins.

## Run it

```bash
pip install game2dboard
python main.py
python -m unittest test_game_logic.py     # 39 tests
```

| Control | Action |
|---|---|
| Click your piece | Select it. Green dots = clone squares, orange rings = jump squares. |
| Click a dot or ring | Move there |
| `U` / `Y` | Undo / redo |
| `R` | Replay the game from the start |
| `N` | New game (same layout) |
| `L` | Next layout: Open, Pillars, Wall, Wall (turned), Diamond, Random |
| `C` | Computer plays blue on/off |
| `Q` / `Esc` | Quit |

## Files

| File | What's in it |
|---|---|
| `game_logic.py` | Rules, layouts, computer player. No graphics, so it can be tested on its own. |
| `main.py` | The game2dboard window: clicks, keys, drawing, replay timer. |
| `dashboard.py` | Side panel: whose turn / who won, piece counts, this game's stats per player, session wins, last moves. Refreshed after every move. |
| `test_game_logic.py` | 39 tests, including corner cases. |
| `img/` | Piece, block and highlight images. |

---

## Course content → where it is in the game

IDs in brackets are the problems from the CE2 review pages that use the same technique.

| Course topic | Where in the game | What problem it solves | Cost |
|---|---|---|---|
| **Matrix validation + `ValueError`** [M1, M2] | `check_square()` | A layout must be exactly 4×4 (or 7×7) before it's used. The length check is inside the loop, before each row is used. | O(n) rows |
| **Two pointers: flip a row** [M2, X832] | `flip_row()` | Mirror a layout left ↔ right | O(n) |
| **Two pointers: flip top ↔ bottom** [M3] | `flip_top_bottom()` | Mirror a layout top ↔ bottom (whole rows are swapped, cells aren't copied) | O(rows) |
| **Transpose** [M4] | `transpose()` | Step 1 of rotating a layout | O(n²) |
| **Rotate = transpose + flip each row** [M4 bonus, L1886] | `rotate_clockwise()` | Makes "Wall (turned)" and random rotated boards | O(n²) |
| **Deep copy vs shallow copy** | `copy_matrix()` | `start_grid` must not change while you play, or the replay breaks | O(n²) |
| **3×3 neighbour window with bounds checks** [HW661, L2373, HW463] | `neighbours()` | Which enemy pieces get captured. Edges and corners just have fewer neighbours. | O(1): 8 checks |
| **BFS on a grid with a queue + visited set** [X994] | `reachable_squares()`, `is_playable()` | A random board must not have squares nobody can ever reach | O(cells) |
| **Hash table of sets** [H2, X217] | `pieces = {RED: set(), BLUE: set()}` | Where each player's pieces are. Counting is `len()`; add/remove/lookup is O(1). No board scan needed. | O(1) |
| **Hash table: square → kind** [H1 value→index pattern] | `targets()` | Highlights and move validation: "is this square a legal target?" is one lookup | O(1) lookup |
| **Hash table as a record** | history entries `{"player", "src", "dst", "kind", "converted", "filled", "ended"}` | Stores exactly what undo needs to reverse a move | O(1) |
| **Derived stats from the stack** | `game_stats()` | Dashboard numbers (moves, clones, jumps, captures) are recomputed from `undo_stack`, so undo/redo can never put them out of sync | O(moves) |
| **Hash table counter** [H5] | `wins` | Games won per player, kept between games | O(1) |
| **Hash table dispatch** | `KEY_ACTIONS` in `main.py` | Key → function, instead of an `if/elif` chain | O(1) |
| **Stack** [X20, X1047, MOCK3] | `undo_stack` | Undo: the last move is reversed first (LIFO) | push/pop O(1) |
| **Second stack** | `redo_stack` | Redo, like a browser's back/forward buttons. A new move clears it. | O(1) |
| **Queue (`deque`)** [HW2073, L1700] | `turns` | Turn order: the front player moves, then goes to the back. Undo rotates it the other way (`appendleft(pop())`). | O(1) |
| **Queue (`deque`)** [X933] | `replay_queue()` | Replay: moves come out oldest first (FIFO). Same moves as the undo stack, read from the other end. | O(1) per step |
| **Sorting** [X215] | `computer_move()`, `scoreboard()` | The computer ranks all legal moves by pieces gained and takes the best. The scoreboard is sorted by wins. | O(m log m) |
| **Big-O thinking** | throughout | Captures check only the 8 squares around the landing square. Piece counts come from set sizes, never a board scan. | |

**Not used: linked lists.** Nothing in the game needs one. Python lists and `deque` already give O(1) at the ends, which is all a stack or queue needs. Forcing one in would just be harder to explain. That's a good answer for "what did you decide not to use, and why?"

## Algorithms

| Algorithm | Where | Complexity | Why this one |
|---|---|---|---|
| **Move generation** | `targets()` | O(24) per piece | Fixed list of 8 clone + 16 jump offsets, each bounds-checked |
| **Capture** | `_apply()` + `neighbours()` | O(8) | Only squares touching the landing square can change |
| **BFS reachability** | `reachable_squares()` | O(cells) | Shortest-path-style flood with a queue. A set stops a square being visited twice. |
| **Random fair board generator** | `random_layout()` | O(cells) per try | Random quarter → mirror with two flips (fair by construction) → maybe rotate → keep only if BFS says every square is reachable |
| **Undo / redo** | `undo()`, `redo()` | O(pieces changed) | Each history entry lists exactly what changed, so undo reverses only that |
| **Greedy computer** | `computer_move()` | O(pieces × 24) + sort | Score every legal move by gain (captures, +1 for a clone), sort, pick the best. Random tie-break so games vary. |
| **End-of-game check** | `_check_end()` | O(pieces) | Stops at the first piece that can move |

## Corner cases handled (and tested)

- Illegal moves are rejected: wrong player's piece, empty square, occupied target, more than 2 away, off the board, onto a block.
- Captures work at edges and corners (bounds checks).
- Undo restores the board, both piece sets, the turn and the win counts exactly. That includes undoing captures, undoing a game-ending move, and undoing on an empty history.
- Redo works after undo, and is cleared by a new move.
- All three game-end cases (wipe-out, full board, stuck player gets the empty squares), plus a draw.
- Every built-in layout and 300 random layouts are fair (mirror-symmetric) and fully reachable.
- 15 computer-vs-computer games finish, and pieces are never lost or duplicated along the way.
- The computer's "thinking" never changes the board. Input is ignored during a replay.

---

## Presentation prep (60% of the grade)

Questions go round-robin, so everyone must be able to explain everything. A possible split (then teach each other):

- **Person A — the board:** matrix helpers, layouts, mirror/rotate, BFS.
- **Person B — the rules:** `pieces` sets, `targets`, captures, undo/redo stacks, turn queue, game end.
- **Person C — the rest:** `main.py` and game2dboard, replay queue, computer player, sorting, tests.

### Draft answers to the professor's five questions

1. **Why Ataxx?** The rules fit in one sentence, but it's a real strategy game. Almost every part of it maps onto something from the course.
2. **Algorithms?** BFS reachability, the random fair board generator, flips/transpose/rotate, bounded neighbour search, greedy move ranking with sorting, undo/redo.
3. **Data structures?** Matrix, sets inside a dict, dicts as lookup tables and records, two stacks, two queues. See the table.
4. **Problems and how they were solved** (swap in the ones you actually run into while building):
   - Random boards sometimes had unreachable squares → BFS check, regenerate.
   - Random boards could favour one player → build from a quarter and mirror it.
   - Undoing a capture → store the converted squares in the history entry.
   - The replay needs the starting board, but a shallow copy would change as you play → `copy_matrix()` makes a real copy.
   - Counting pieces by scanning the board was wasteful → sets give `len()` in O(1).
5. **Postponed:**
   - A minimax computer that thinks several moves ahead (needs recursion and game trees).
   - Saving games to a file.
   - Board sizes other than 7×7.

### Test yourselves (answer without looking)

- Why does `mirror_quarter` use `row[:HALF - 1]` and `top_half[:HALF - 1]`, not the whole row/half?
- Why is `[[None] * 7] * 7` a bug, and `[row[:] for row in m]` correct?
- What would break in BFS without the `seen` set?
- Why rotate the turn queue backwards on undo, instead of just rotating it forwards again?
- Why can a capture only affect the 8 squares around the landing square?
- What's the worst-case cost of `computer_move()` on a full board?
