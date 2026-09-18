"""Hungarian two-player Cassino, played with a 52-card French deck.

Cards are strings: rank, then suit.
Ranks: A 2 3 4 5 6 7 8 9 10 J Q K. Suits: S H D C.
"""
from itertools import combinations
from typing import NamedTuple, Optional

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
RANK_VALUE = {r: i + 1 for i, r in enumerate(RANKS)}


def value(card):
    """The card's value: A=1 ... 9=9, 10=10, J=11, Q=12, K=13."""
    return RANK_VALUE[card[:-1]]


class Move(NamedTuple):
    """What a player plays from hand, and what they take from the table."""
    hand: frozenset
    table: frozenset


class State(NamedTuple):
    hands: tuple
    table: tuple
    talon: tuple
    piles: tuple
    sweeps: tuple
    player: int
    last_capturer: Optional[int] = None


def new_deal(deck, first=0):
    """Deal from `deck`: 3 cards to `first`, 3 to the other, 4 to the table."""
    other = 1 - first
    hands = [None, None]
    hands[first] = tuple(deck[0:3])
    hands[other] = tuple(deck[3:6])
    return State(
        hands=(hands[0], hands[1]),
        table=tuple(deck[6:10]),
        talon=tuple(deck[10:]),
        piles=((), ()),
        sweeps=(0, 0),
        player=first,
        last_capturer=None,
    )


def _subsets(cards):
    """Every non-empty subset of `cards`, as frozensets."""
    cards = list(cards)
    result = []
    for r in range(1, len(cards) + 1):
        for combo in combinations(cards, r):
            result.append(frozenset(combo))
    return result


def legal_moves(state):
    """Every legal Move for the player to move."""
    hand = state.hands[state.player]
    table = state.table
    moves = {Move(frozenset({c}), frozenset()) for c in hand}

    table_by_sum = {}
    for ts in _subsets(table):
        table_by_sum.setdefault(sum(value(c) for c in ts), []).append(ts)

    for hs in _subsets(hand):
        total = sum(value(c) for c in hs)
        for ts in table_by_sum.get(total, []):
            moves.add(Move(hs, ts))

    return moves


def play(state, move):
    """The state after `move`, including everything the rules make happen
    before the next move. Raises ValueError if the move is not legal."""
    if move not in legal_moves(state):
        raise ValueError(f"illegal move: {move}")

    player = state.player
    opponent = 1 - player
    hands = [list(state.hands[0]), list(state.hands[1])]
    for c in move.hand:
        hands[player].remove(c)

    table = list(state.table)
    piles = [list(state.piles[0]), list(state.piles[1])]
    sweeps = list(state.sweeps)
    last_capturer = state.last_capturer
    table_was_empty = len(table) == 0

    if move.table:
        for c in move.table:
            table.remove(c)
        piles[player].extend(move.hand)
        piles[player].extend(move.table)
        last_capturer = player
        if not table:
            sweeps[player] += 1
        next_player = opponent
    else:
        table.extend(move.hand)
        next_player = player if (table_was_empty and hands[player]) else opponent

    if not hands[next_player] and hands[1 - next_player]:
        next_player = 1 - next_player

    talon = state.talon
    if not hands[0] and not hands[1]:
        if talon:
            leader = last_capturer if last_capturer is not None else next_player
            new_hands = [None, None]
            new_hands[leader] = talon[0:3]
            new_hands[1 - leader] = talon[3:6]
            hands = new_hands
            talon = talon[6:]
            next_player = leader
        elif table and last_capturer is not None:
            piles[last_capturer].extend(table)
            table = []
            next_player = last_capturer

    return State(
        hands=(tuple(hands[0]), tuple(hands[1])),
        table=tuple(table),
        talon=tuple(talon),
        piles=(tuple(piles[0]), tuple(piles[1])),
        sweeps=tuple(sweeps),
        player=next_player,
        last_capturer=last_capturer,
    )


def deal_over(state):
    """True once every card has been taken."""
    return (not state.hands[0] and not state.hands[1]
            and not state.table and not state.talon)


def score(state):
    """A pair: the points each player earned in the finished deal."""
    points = []
    for p in (0, 1):
        pile = state.piles[p]
        points.append(
            (3 if len(pile) >= 27 else 0)
            + (2 if sum(c.endswith("S") for c in pile) >= 7 else 0)
            + sum(c.startswith("A") for c in pile)
            + (2 if "10D" in pile else 0)
            + (1 if "2S" in pile else 0)
            + state.sweeps[p]
        )
    return tuple(points)
