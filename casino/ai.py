"""A simple computer opponent."""
import random

from . import legal_moves, value

# Cards worth chasing when a capture choice is otherwise a toss-up.
_BONUS = {"10D": 2, "2S": 1}


def _capture_bonus(move):
    bonus = sum(_BONUS.get(c, 0) for c in move.table)
    bonus += sum(1 for c in move.table if c.startswith("A"))
    bonus += sum(1 for c in move.table if c.endswith("S"))
    return bonus


def choose_move(state, rng=random):
    """Prefer the biggest, most valuable capture; otherwise trail low."""
    moves = list(legal_moves(state))
    captures = [m for m in moves if m.table]
    if captures:
        best = max(len(m.table) for m in captures)
        best_bonus = max(_capture_bonus(m) for m in captures if len(m.table) == best)
        top = [m for m in captures
               if len(m.table) == best and _capture_bonus(m) == best_bonus]
        return rng.choice(top)

    placements = [m for m in moves if not m.table]
    lowest = min(value(next(iter(m.hand))) for m in placements)
    top = [m for m in placements if value(next(iter(m.hand))) == lowest]
    return rng.choice(top)
