"""
Tests for the rules and corner cases. Run with:
    python -m unittest test_game_logic.py
"""

import random
import unittest
from game_logic import (Ataxx, SIZE, RED, BLUE, BLOCK, EMPTY, LAYOUT_NAMES, QUARTERS,
                        check_square, copy_matrix, flip_row, flip_top_bottom, transpose,
                        rotate_clockwise, mirror_quarter, build_layout, is_playable,
                        reachable_squares)


def empty_board(game):
    """Clear the board and remove all pieces, so a test can place its own."""
    game.grid = [[EMPTY] * SIZE for _ in range(SIZE)]
    game.pieces = {RED: set(), BLUE: set()}


def place(game, player, *cells):
    for r, c in cells:
        game.grid[r][c] = player
        game.pieces[player].add((r, c))


def snapshot(game):
    return (copy_matrix(game.grid), {p: set(s) for p, s in game.pieces.items()},
            list(game.turns), dict(game.wins), game.over)


class TestMatrixHelpers(unittest.TestCase):

    def test_check_square_accepts_good_matrix(self):
        check_square([[1, 2], [3, 4]], 2)

    def test_check_square_rejects_ragged_and_wrong_size(self):
        with self.assertRaises(ValueError):
            check_square([[1, 2], [3]], 2)
        with self.assertRaises(ValueError):
            check_square([[1, 2]], 2)

    def test_flip_row_returns_copy(self):
        row = [1, 2, 3]
        self.assertEqual(flip_row(row), [3, 2, 1])
        self.assertEqual(row, [1, 2, 3])

    def test_flip_top_bottom(self):
        self.assertEqual(flip_top_bottom([[1], [2], [3]]), [[3], [2], [1]])

    def test_transpose_non_square(self):
        self.assertEqual(transpose([[1, 2, 3], [4, 5, 6]]), [[1, 4], [2, 5], [3, 6]])

    def test_rotate_clockwise(self):
        self.assertEqual(rotate_clockwise([[1, 2], [3, 4]]), [[3, 1], [4, 2]])

    def test_copy_matrix_is_deep(self):
        m = [[1, 2], [3, 4]]
        c = copy_matrix(m)
        c[0][0] = 99
        self.assertEqual(m[0][0], 1)

    def test_mirror_quarter_shape_and_symmetry(self):
        full = mirror_quarter(QUARTERS["Pillars"])
        check_square(full, SIZE)
        for row in full:
            self.assertEqual(row, flip_row(row))              # left-right symmetric
        self.assertEqual(full, flip_top_bottom(copy_matrix(full)))   # top-bottom symmetric
        self.assertEqual(full[1][1], "#")
        self.assertEqual(full[5][5], "#")

    def test_mirror_rejects_bad_quarter(self):
        with self.assertRaises(ValueError):
            mirror_quarter(["...", "...", "...", "..."])



class TestGameStats(unittest.TestCase):

    def test_stats_follow_moves_and_undo(self):
        game = Ataxx(seed=1)
        game.new_game("Open")
        self.assertEqual(game.game_stats()[RED]["moves"], 0)
        game.move((0, 0), (1, 1))            # red clone
        game.move((0, SIZE - 1), (2, SIZE - 1))   # blue jump
        stats = game.game_stats()
        self.assertEqual((stats[RED]["moves"], stats[RED]["clones"]), (1, 1))
        self.assertEqual((stats[BLUE]["moves"], stats[BLUE]["jumps"]), (1, 1))
        game.undo()
        self.assertEqual(game.game_stats()[BLUE]["moves"], 0)
        game.redo()
        self.assertEqual(game.game_stats()[BLUE]["jumps"], 1)

    def test_stats_count_captures(self):
        game = Ataxx(seed=1)
        empty_board(game)
        place(game, RED, (3, 3))
        place(game, BLUE, (3, 5), (2, 5), (6, 6))
        game.move((3, 3), (3, 4))            # clone next to two blue pieces
        self.assertEqual(game.game_stats()[RED]["captured"], 2)
        self.assertEqual(game.game_stats()[RED]["best"], 2)

class TestLayouts(unittest.TestCase):

    def test_every_layout_is_fair_and_playable(self):
        rng = random.Random(1)
        for name in LAYOUT_NAMES:
            layout = build_layout(name, rng)
            check_square(layout, SIZE)
            self.assertTrue(is_playable(layout), name)
            for r, c in [(0, 0), (0, 6), (6, 0), (6, 6)]:
                self.assertNotEqual(layout[r][c], "#", name)

    def test_random_layouts_always_playable(self):
        rng = random.Random(7)
        for _ in range(300):
            layout = build_layout("Random", rng)
            self.assertTrue(is_playable(layout))
            for row in layout:
                self.assertEqual(row, flip_row(row))    # still fair

    def test_bfs_finds_a_cut_off_square(self):
        # A square boxed in by a 2-thick wall can't be reached even by jumping.
        layout = [list(".......") for _ in range(SIZE)]
        for r in range(SIZE):
            for c in range(SIZE):
                if max(abs(r - 3), abs(c - 3)) in (1, 2):
                    layout[r][c] = "#"
        self.assertFalse(is_playable(layout))
        self.assertNotIn((3, 3), reachable_squares(layout, (0, 0)))

    def test_turned_wall_differs_from_wall(self):
        rng = random.Random(0)
        self.assertNotEqual(build_layout("Wall", rng), build_layout("Wall (turned)", rng))


class TestMoves(unittest.TestCase):

    def setUp(self):
        self.g = Ataxx(seed=0)   # "Open" layout

    def test_start_position(self):
        self.assertEqual(self.g.count(RED), 2)
        self.assertEqual(self.g.count(BLUE), 2)
        self.assertEqual(self.g.current_player(), RED)

    def test_targets_from_corner(self):
        t = self.g.targets(0, 0)
        self.assertEqual(sum(1 for k in t.values() if k == "clone"), 3)
        self.assertEqual(sum(1 for k in t.values() if k == "jump"), 5)

    def test_clone_keeps_original(self):
        self.g.move((0, 0), (1, 1))
        self.assertEqual(self.g.grid[0][0], RED)
        self.assertEqual(self.g.grid[1][1], RED)
        self.assertEqual(self.g.count(RED), 3)
        self.assertEqual(self.g.current_player(), BLUE)

    def test_jump_moves_the_piece(self):
        self.g.move((0, 0), (2, 2))
        self.assertIsNone(self.g.grid[0][0])
        self.assertEqual(self.g.count(RED), 2)

    def test_capture_converts_all_neighbours(self):
        empty_board(self.g)
        place(self.g, RED, (3, 1))
        place(self.g, BLUE, (2, 3), (3, 3), (4, 4), (6, 6))
        self.g.move((3, 1), (3, 2))   # clone next to (2,3) and (3,3); (4,4) is not adjacent
        self.assertEqual(self.g.grid[2][3], RED)
        self.assertEqual(self.g.grid[3][3], RED)
        self.assertEqual(self.g.grid[4][4], BLUE)
        self.assertEqual(self.g.count(RED), 4)
        self.assertEqual(self.g.count(BLUE), 2)

    def test_capture_at_board_edge(self):
        empty_board(self.g)
        place(self.g, RED, (0, 2))
        place(self.g, BLUE, (0, 0), (6, 6))
        self.g.move((0, 2), (0, 1))
        self.assertEqual(self.g.grid[0][0], RED)

    def test_illegal_moves_are_rejected(self):
        g = self.g
        self.assertIsNone(g.move((0, 6), (1, 5)))   # blue piece on red's turn
        self.assertIsNone(g.move((3, 3), (3, 4)))   # no piece there
        self.assertIsNone(g.move((0, 0), (0, 3)))   # 3 squares away
        self.assertIsNone(g.move((0, 0), (-1, 0)))  # off the board
        g.move((0, 0), (1, 1))
        g.move((0, 6), (1, 5))
        self.assertIsNone(g.move((0, 0), (1, 1)))   # occupied
        self.assertEqual(len(g.undo_stack), 2)

    def test_cannot_move_onto_block(self):
        g = Ataxx(seed=0)
        g.new_game("Pillars")                        # block at (1, 1)
        self.assertEqual(g.grid[1][1], BLOCK)
        self.assertIsNone(g.move((0, 0), (1, 1)))
        self.assertNotIn((1, 1), g.targets(0, 0))


class TestUndoRedo(unittest.TestCase):

    def test_undo_restores_everything(self):
        g = Ataxx(seed=0)
        before = snapshot(g)
        g.move((0, 0), (1, 1))
        g.move((0, 6), (2, 4))
        g.undo()
        g.undo()
        self.assertEqual(snapshot(g), before)

    def test_undo_a_capture(self):
        g = Ataxx(seed=0)
        empty_board(g)
        place(g, RED, (3, 1))
        place(g, BLUE, (3, 3), (6, 6))
        before = snapshot(g)
        g.move((3, 1), (3, 2))
        g.undo()
        self.assertEqual(snapshot(g), before)

    def test_undo_on_empty_history(self):
        self.assertIsNone(Ataxx(seed=0).undo())

    def test_redo_after_undo(self):
        g = Ataxx(seed=0)
        g.move((0, 0), (1, 1))
        after = snapshot(g)
        g.undo()
        g.redo()
        self.assertEqual(snapshot(g), after)

    def test_new_move_clears_redo(self):
        g = Ataxx(seed=0)
        g.move((0, 0), (1, 1))
        g.undo()
        g.move((0, 0), (0, 1))
        self.assertIsNone(g.redo())


class TestGameEnd(unittest.TestCase):

    def test_wiping_out_the_opponent_ends_the_game(self):
        g = Ataxx(seed=0)
        empty_board(g)
        place(g, RED, (3, 1))
        place(g, BLUE, (3, 3))
        g.move((3, 1), (3, 2))
        self.assertTrue(g.over)
        self.assertEqual(g.winner, RED)
        self.assertEqual(g.wins[RED], 1)
        self.assertIsNone(g.move((3, 2), (4, 2)))   # no moves after the end

    def test_stuck_player_gives_away_empty_squares(self):
        g = Ataxx(seed=0)
        # Fill the board: blue is boxed in at (0,0) by red, and two squares far away are empty.
        g.grid = [[RED] * SIZE for _ in range(SIZE)]
        g.pieces = {RED: set(), BLUE: set()}
        for r in range(SIZE):
            for c in range(SIZE):
                g.pieces[RED].add((r, c))
        g.grid[0][0] = BLUE
        g.pieces[RED].remove((0, 0))
        g.pieces[BLUE].add((0, 0))
        for r, c in [(6, 6), (6, 5)]:
            g.grid[r][c] = EMPTY
            g.pieces[RED].remove((r, c))
        # Red clones into (6,5); blue (at 0,0) can't move, so red gets (6,6).
        g.move((5, 5), (6, 5))
        self.assertTrue(g.over)
        self.assertEqual(g.grid[6][6], RED)
        self.assertEqual(g.winner, RED)

    def test_full_board_ends_the_game(self):
        g = Ataxx(seed=0)
        g.grid = [[BLUE] * SIZE for _ in range(SIZE)]
        g.pieces = {RED: set(), BLUE: {(r, c) for r in range(SIZE) for c in range(SIZE)}}
        for cell in [(0, 0), (0, 1)]:
            g.grid[cell[0]][cell[1]] = RED
            g.pieces[BLUE].discard(cell)
            g.pieces[RED].add(cell)
        g.grid[0][2] = EMPTY
        g.pieces[BLUE].discard((0, 2))
        g.move((0, 1), (0, 2))
        self.assertTrue(g.over)
        self.assertEqual(g.empty_squares(), [])

    def test_undo_after_game_over(self):
        g = Ataxx(seed=0)
        empty_board(g)
        place(g, RED, (3, 1))
        place(g, BLUE, (3, 3))
        before = snapshot(g)
        g.move((3, 1), (3, 2))
        g.undo()
        self.assertEqual(snapshot(g), before)
        self.assertEqual(g.wins[RED], 0)

    def test_draw(self):
        g = Ataxx(seed=0)
        # Everything blocked except one empty square; red fills it and nothing is captured.
        g.grid = [[BLOCK] * SIZE for _ in range(SIZE)]
        g.pieces = {RED: set(), BLUE: set()}
        g.grid[0][1] = EMPTY
        place(g, RED, (0, 0), (1, 0))
        place(g, BLUE, (0, 3), (0, 4), (0, 5))
        g.move((0, 0), (0, 1))          # red 3, blue 3, board full
        self.assertTrue(g.over)
        self.assertEqual(g.winner, "draw")
        self.assertEqual(g.wins["draws"], 1)


class TestComputer(unittest.TestCase):

    def test_takes_the_biggest_capture(self):
        g = Ataxx(seed=0)
        empty_board(g)
        place(g, RED, (3, 0))
        place(g, BLUE, (2, 2), (3, 2), (4, 2), (6, 6))
        src, dst = g.computer_move()
        self.assertEqual(dst, (3, 1))     # touches all three blue pieces, and it's a clone

    def test_does_not_change_the_board(self):
        g = Ataxx(seed=0)
        before = snapshot(g)
        g.computer_move()
        self.assertEqual(snapshot(g), before)

    def test_computer_vs_computer_games_finish(self):
        for seed in range(15):
            g = Ataxx(seed=seed)
            g.new_game(LAYOUT_NAMES[seed % len(LAYOUT_NAMES)])
            moves = 0
            while not g.over and moves < 500:
                src, dst = g.computer_move()
                self.assertIsNotNone(g.move(src, dst))
                moves += 1
                total = g.count(RED) + g.count(BLUE) + len(g.empty_squares())
                blocks = sum(row.count(BLOCK) for row in g.grid)
                self.assertEqual(total + blocks, SIZE * SIZE)   # no piece lost or duplicated
            self.assertTrue(g.over)


class TestReplayAndScores(unittest.TestCase):

    def test_replay_order(self):
        g = Ataxx(seed=0)
        g.move((0, 0), (1, 1))
        g.move((0, 6), (1, 5))
        q = g.replay_queue()
        self.assertEqual(q.popleft()["dst"], (1, 1))
        self.assertEqual(q.popleft()["dst"], (1, 5))
        self.assertEqual(len(g.undo_stack), 2)

    def test_start_grid_is_a_real_copy(self):
        g = Ataxx(seed=0)
        g.move((0, 0), (1, 1))
        self.assertIsNone(g.start_grid[1][1])

    def test_scoreboard_sorted(self):
        g = Ataxx(seed=0)
        g.wins = {RED: 1, BLUE: 3, "draws": 0}
        self.assertTrue(g.scoreboard().startswith("Blue: 3"))


if __name__ == "__main__":
    unittest.main()
