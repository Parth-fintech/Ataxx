"""
Ataxx - the dashboard panel beside the board (plain tkinter).
Shows whose turn it is (or who won), piece counts, this game's stats per
player, session wins and the last few moves. main.py calls update() after
every move, undo, redo and new game.
"""

import tkinter as tk
from game_logic import SIZE, RED, BLUE

BG = "#2b2e36"
PANEL = "#353944"
TEXT = "#f2efe8"
MUTED = "#9aa0ab"
DRAW_COLOR = "#6b7280"
COLOR = {RED: "#d9473f", BLUE: "#3a78d6"}
WIDTH = 290
LOG_LINES = 9

STAT_ROWS = [("Moves", "moves"), ("Clones", "clones"), ("Jumps", "jumps"),
             ("Pieces captured", "captured"), ("Best single capture", "best")]


def square_name(square):
    """(row, col) -> chess-style name: columns a-g, row 1 at the bottom."""
    r, c = square
    return f"{'abcdefg'[c]}{SIZE - r}"


class Dashboard:

    def __init__(self, root):
        self.frame = tk.Frame(root, bg=BG)
        self.frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 10), pady=10)
        tk.Frame(self.frame, bg=BG, width=WIDTH, height=0).pack()   # fixes the width

        self.banner = tk.Label(self.frame, font=("Helvetica", 20, "bold"),
                               fg="white", pady=10)
        self.banner.pack(fill=tk.X)
        self.subtitle = tk.Label(self.frame, bg=BG, fg=MUTED, font=("Helvetica", 11))
        self.subtitle.pack(fill=tk.X, pady=(4, 0))

        # Pieces on the board
        box = self._section("PIECES ON BOARD")
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill=tk.X)
        self.red_count = tk.Label(row, bg=PANEL, fg=COLOR[RED], font=("Helvetica", 16, "bold"))
        self.red_count.pack(side=tk.LEFT)
        self.blue_count = tk.Label(row, bg=PANEL, fg=COLOR[BLUE], font=("Helvetica", 16, "bold"))
        self.blue_count.pack(side=tk.RIGHT)
        self.bar = tk.Canvas(box, height=12, width=WIDTH - 20, bg=BG, highlightthickness=0)
        self.bar.pack(pady=(4, 0))

        # This game: one row per stat, one column per player
        box = self._section("THIS GAME")
        table = tk.Frame(box, bg=PANEL)
        table.pack(fill=tk.X)
        table.columnconfigure(0, weight=1)
        for col, (name, color) in enumerate([("Red", COLOR[RED]), ("Blue", COLOR[BLUE])], 1):
            tk.Label(table, text=name, bg=PANEL, fg=color, width=5,
                     font=("Helvetica", 11, "bold")).grid(row=0, column=col)
        self.stat_cells = {}
        for i, (label, key) in enumerate(STAT_ROWS, 1):
            tk.Label(table, text=label, bg=PANEL, fg=TEXT, anchor="w",
                     font=("Helvetica", 11)).grid(row=i, column=0, sticky="w")
            for col, player in enumerate((RED, BLUE), 1):
                cell = tk.Label(table, bg=PANEL, fg=TEXT, font=("Helvetica", 11))
                cell.grid(row=i, column=col)
                self.stat_cells[(key, player)] = cell

        # Wins across games (kept until the window is closed)
        box = self._section("SESSION WINS")
        row = tk.Frame(box, bg=PANEL)
        row.pack(fill=tk.X)
        self.win_labels = {}
        for key, name, color in [(RED, "Red", COLOR[RED]), ("draws", "Draws", MUTED),
                                 (BLUE, "Blue", COLOR[BLUE])]:
            cell = tk.Frame(row, bg=PANEL)
            cell.pack(side=tk.LEFT, expand=True)
            number = tk.Label(cell, bg=PANEL, fg=color, font=("Helvetica", 20, "bold"))
            number.pack()
            tk.Label(cell, text=name, bg=PANEL, fg=MUTED, font=("Helvetica", 10)).pack()
            self.win_labels[key] = number

        # Move log, newest first, each line in the mover's colour
        box = self._section("LAST MOVES")
        self.log = tk.Text(box, height=LOG_LINES, width=30, bg=PANEL, fg=TEXT, bd=0,
                           highlightthickness=0, font=("Menlo", 11), cursor="arrow")
        self.log.pack(fill=tk.X)
        self.log.tag_configure(RED, foreground=COLOR[RED])
        self.log.tag_configure(BLUE, foreground=COLOR[BLUE])
        self.log.tag_configure("muted", foreground=MUTED)

    def _section(self, title):
        tk.Label(self.frame, text=title, bg=BG, fg=MUTED, anchor="w",
                 font=("Helvetica", 10, "bold")).pack(fill=tk.X, pady=(12, 2))
        box = tk.Frame(self.frame, bg=PANEL, padx=10, pady=8)
        box.pack(fill=tk.X)
        return box

    def update(self, game, vs_computer):
        red, blue = game.count(RED), game.count(BLUE)

        # Banner: whose turn, or the result
        if game.over and game.winner == "draw":
            self.banner.config(text=f"DRAW  {red}-{blue}", bg=DRAW_COLOR)
        elif game.over:
            self.banner.config(text=f"{game.winner.upper()} WINS  {max(red, blue)}-{min(red, blue)}",
                               bg=COLOR[game.winner])
        else:
            player = game.current_player()
            who = "  (computer)" if vs_computer and player == BLUE else ""
            self.banner.config(text=f"{player.upper()} TO MOVE{who}", bg=COLOR[player])
        self.subtitle.config(text=f"Move {len(game.undo_stack)}   ·   {game.layout_name}   ·   "
                                  f"Computer {'ON' if vs_computer else 'OFF'}")

        # Piece counts + a split bar
        self.red_count.config(text=f"Red {red}")
        self.blue_count.config(text=f"{blue} Blue")
        self.bar.delete("all")
        width = WIDTH - 20
        split = width * red // (red + blue) if red + blue else width // 2
        self.bar.create_rectangle(0, 0, split, 12, fill=COLOR[RED], width=0)
        self.bar.create_rectangle(split, 0, width, 12, fill=COLOR[BLUE], width=0)

        # This game's stats
        stats = game.game_stats()
        for _, key in STAT_ROWS:
            for player in (RED, BLUE):
                self.stat_cells[(key, player)].config(text=str(stats[player][key]))

        # Session wins
        for key, label in self.win_labels.items():
            label.config(text=str(game.wins[key]))

        # Move log
        self.log.config(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        history = game.undo_stack
        if not history:
            self.log.insert(tk.END, "No moves yet.", "muted")
        start = max(0, len(history) - LOG_LINES)
        for number in range(len(history), start, -1):        # newest first
            entry = history[number - 1]
            line = (f"{number:>3}. {entry['player'].capitalize():<4} {entry['kind']:<5} "
                    f"{square_name(entry['src'])}>{square_name(entry['dst'])}")
            if entry["converted"]:
                line += f"  +{len(entry['converted'])}"
            if entry["filled"]:
                line += f"  fills {len(entry['filled'])}"
            self.log.insert(tk.END, line + ("\n" if number - 1 > start else ""), entry["player"])
        self.log.config(state=tk.DISABLED)
