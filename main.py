"""
Ataxx - the window (game2dboard). Run with:  python main.py

Click one of your pieces: green dots = clone there (1 square, you keep the
original), orange rings = jump there (2 squares, the piece moves). Enemy pieces
touching where you land become yours.

Keys:  U undo   Y redo   R replay   N new game   L next layout
       C computer plays blue on/off   Q / Esc quit
"""

from game2dboard import Board
from game_logic import Ataxx, SIZE, RED, BLUE, BLOCK, EMPTY
from dashboard import Dashboard, COLOR, DRAW_COLOR

CELL_SIZE = 80
TICK_MS = 450            # replay speed
COMPUTER_DELAY_MS = 450

game = Ataxx()
board = Board(SIZE, SIZE)

selected = None          # (row, col) of the selected piece, or None
targets = {}             # hash table: square -> "clone"/"jump" for the selected piece
vs_computer = False
replay_moves = None      # replay queue while a replay runs, otherwise None


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------

def cell_image(r, c):
    if (r, c) in targets:                  # dict lookup, O(1)
        return targets[(r, c)]             # "clone" or "jump" image
    value = game.grid[r][c]
    if value is EMPTY:
        return "empty"
    if (r, c) == selected:
        return value + "_sel"
    return value                           # "red", "blue" or "block"


def draw(note=None):
    for r in range(SIZE):
        for c in range(SIZE):
            board[r][c] = cell_image(r, c)
    show_status(note)
    dashboard.update(game, vs_computer)
    show_win_banner()


def show_win_banner():
    """When the game is over, draw a strip across the middle of the board
    saying who won and the session score. Removed again on undo / new game."""
    canvas = board._canvas                 # game2dboard's tkinter canvas
    canvas.delete("banner")
    if not game.over or replay_moves is not None:
        return
    red, blue = game.count(RED), game.count(BLUE)
    if game.winner == "draw":
        title, color = f"IT'S A DRAW  {red}-{blue}", DRAW_COLOR
    else:
        title = f"{game.winner.upper()} WINS!  {max(red, blue)}-{min(red, blue)}"
        color = COLOR[game.winner]
    w = board._canvas_width
    mid = board._canvas_height // 2
    canvas.create_rectangle(0, mid - 75, w, mid + 75, fill=color, outline="", tags="banner")
    canvas.create_text(w // 2, mid - 30, text=title, fill="white",
                       font=("Helvetica", 34, "bold"), tags="banner")
    canvas.create_text(w // 2, mid + 12, fill="white", font=("Helvetica", 15), tags="banner",
                       text=f"Session:  Red {game.wins[RED]}   ·   Blue {game.wins[BLUE]}"
                            f"   ·   Draws {game.wins['draws']}")
    canvas.create_text(w // 2, mid + 45, fill="white", font=("Helvetica", 12), tags="banner",
                       text="N  play again      L  next layout      R  replay      U  undo")


def show_status(note=None):
    red, blue = game.count(RED), game.count(BLUE)
    if note:
        line1 = note
    elif game.over:
        if game.winner == "draw":
            line1 = f"Draw, {red}-{blue}.   N: play again   L: next layout   R: replay"
        else:
            line1 = f"{game.winner.upper()} WINS {max(red, blue)}-{min(red, blue)}!   N: again   L: next layout   R: replay"
    else:
        player = game.current_player()
        who = "computer" if (vs_computer and player == BLUE) else "pick a piece"
        line1 = f"{player.upper()} to move ({who})"
    keys = "U undo   Y redo   R replay   N new   L layout   C computer   Q quit"
    board.print(line1 + "\n" + keys)


def clear_selection():
    global selected, targets
    selected = None
    targets = {}


# ----------------------------------------------------------------------
# Actions
# ----------------------------------------------------------------------

def on_click(button, r, c):
    global selected, targets
    if replay_moves is not None:
        return
    if game.over:
        draw("Game over - N: play again, L: next layout, U: undo")
        return
    if vs_computer and game.current_player() == BLUE:
        return

    if selected is not None and (r, c) in targets:          # second click: move
        game.move(selected, (r, c))
        clear_selection()
        draw()
        computer_turn()
    elif game.grid[r][c] == game.current_player():          # first click: select
        selected = (r, c)
        targets = game.targets(r, c)
        draw(None if targets else "That piece is boxed in - pick another one.")
    else:                                                   # anything else: cancel
        clear_selection()
        if game.grid[r][c] == BLOCK:
            draw("That square is blocked.")
        elif game.grid[r][c] not in (EMPTY, BLOCK):
            draw("That's not your piece.")
        else:
            draw()


def computer_turn():
    global selected, targets
    if not vs_computer or game.over or game.current_player() != BLUE:
        return
    board.pause(COMPUTER_DELAY_MS, change_cursor=False)
    move = game.computer_move()
    if move is None:
        return
    src, dst = move
    selected, targets = src, {dst: game.targets(*src)[dst]}   # show what it is about to do
    draw("Computer is moving...")
    board.pause(COMPUTER_DELAY_MS, change_cursor=False)
    game.move(src, dst)
    clear_selection()
    draw()


def undo_move():
    if replay_moves is not None:
        return
    clear_selection()
    if game.undo() is None:
        draw("Nothing to undo.")
        return
    if vs_computer and game.current_player() == BLUE:   # also undo the computer's reply
        game.undo()
    draw()


def redo_move():
    if replay_moves is not None:
        return
    clear_selection()
    if game.redo() is None:
        draw("Nothing to redo.")
        return
    if vs_computer and game.current_player() == BLUE and game.redo_stack:
        game.redo()
    draw()


def new_game():
    global replay_moves
    replay_moves = None
    clear_selection()
    game.new_game()
    draw()


def next_layout():
    global replay_moves
    replay_moves = None
    clear_selection()
    game.next_layout()
    draw()


def toggle_computer():
    global vs_computer
    if replay_moves is not None:
        return
    vs_computer = not vs_computer
    clear_selection()
    draw()
    computer_turn()


def start_replay():
    """Show the game again from the start: moves come out of a queue, oldest first."""
    global replay_moves
    if replay_moves is not None:
        return
    if not game.undo_stack:
        draw("Nothing to replay yet.")
        return
    clear_selection()
    replay_moves = game.replay_queue()
    board._canvas.delete("banner")
    for r in range(SIZE):
        for c in range(SIZE):
            value = game.start_grid[r][c]
            board[r][c] = "empty" if value is EMPTY else value
    show_status("Replaying...")


def replay_step():
    global replay_moves
    if replay_moves is None:
        return
    if not replay_moves:                       # queue empty: replay finished
        replay_moves = None
        draw()
        return
    entry = replay_moves.popleft()             # DEQUEUE the oldest move
    player = entry["player"]
    if entry["kind"] == "jump":
        board[entry["src"][0]][entry["src"][1]] = "empty"
    board[entry["dst"][0]][entry["dst"][1]] = player
    for r, c in entry["converted"] + entry["filled"]:
        board[r][c] = player


def quit_game():
    board.close()


# Hash table: key -> action (instead of a long if/elif chain)
KEY_ACTIONS = {
    "u": undo_move,
    "y": redo_move,
    "r": start_replay,
    "n": new_game,
    "l": next_layout,
    "c": toggle_computer,
    "q": quit_game,
    "escape": quit_game,
}


def on_key(key):
    action = KEY_ACTIONS.get(key.lower())
    if action:
        action()


def on_start():
    draw()
    board.start_timer(TICK_MS)


# ----------------------------------------------------------------------
# Window setup
# ----------------------------------------------------------------------

board.title = "Ataxx"
board.cell_size = CELL_SIZE
board.cell_spacing = 3
board.grid_color = "#2b2e36"
board.margin_color = "#2b2e36"
board.cell_color = "#e9e4d8"
board.margin = 10
board.create_output(color="#f2efe8", background_color="#2b2e36", font_size=11)
dashboard = Dashboard(board._root)         # panel to the right of the board

board.on_mouse_click = on_click
board.on_key_press = on_key
board.on_timer = replay_step
board.on_start = on_start

board.show()
