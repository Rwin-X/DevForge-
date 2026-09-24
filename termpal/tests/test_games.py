"""Headless tests for termpal.core.games."""

from termpal.core.games import CatchGame, GuessGame


def test_guess_game_correct_answer_wins():
    game = GuessGame(low=1, high=10, target=7, max_attempts=5)
    result = game.guess(7)
    assert game.finished
    assert game.won
    assert "Correct" in result


def test_guess_game_gives_direction_hints():
    game = GuessGame(low=1, high=10, target=7, max_attempts=5)
    result = game.guess(3)
    assert "higher" in result
    assert not game.finished


def test_guess_game_runs_out_of_attempts():
    game = GuessGame(low=1, high=10, target=7, max_attempts=2)
    game.guess(1)
    result = game.guess(2)
    assert game.finished
    assert not game.won
    assert "Out of attempts" in result


def test_guess_game_ignores_input_after_finished():
    game = GuessGame(low=1, high=10, target=7, max_attempts=5)
    game.guess(7)
    result = game.guess(3)
    assert "already over" in result


def test_catch_game_scores_on_hit():
    game = CatchGame(track_width=10, rounds=3, target_position=4)
    hit = game.attempt_catch(4)
    assert hit
    assert game.score == 1


def test_catch_game_no_score_on_miss():
    game = CatchGame(track_width=10, rounds=3, target_position=4)
    hit = game.attempt_catch(9)
    assert not hit
    assert game.score == 0


def test_catch_game_finishes_after_all_rounds():
    game = CatchGame(track_width=10, rounds=2, target_position=5)
    game.attempt_catch(5)
    assert not game.finished
    game.attempt_catch(0)
    assert game.finished


def test_catch_game_result_summary_format():
    # Only the first catch is guaranteed to land on the seeded target -
    # attempt_catch re-randomizes target_position for the next round.
    # The summary format itself is what's under test here.
    game = CatchGame(track_width=10, rounds=2, target_position=5)
    game.attempt_catch(5)
    game.attempt_catch(0)
    assert game.result_summary() in ("Caught 1 of 2.", "Caught 2 of 2.")


def test_catch_game_constructor_seed_is_not_overwritten_by_post_init():
    # Regression test: __post_init__ must not clobber an explicitly
    # passed target_position with a fresh random value.
    game = CatchGame(track_width=10, target_position=3)
    assert game.target_position == 3


def test_catch_game_default_construction_still_randomizes():
    game = CatchGame(track_width=10)
    assert 0 <= game.target_position <= 9


def test_catch_game_target_position_always_single_digit_at_default_ui_width():
    # The curses overlay only accepts single-digit keypresses (0-9) and
    # draws a 10-cell track, so the game must never generate a target
    # position the UI cannot represent. Regression test for a mismatch
    # between App's CatchGame construction and the overlay's input range.
    for _ in range(200):
        game = CatchGame(track_width=10)
        assert 0 <= game.target_position <= 9
