# Session Notes

## Issues Found and Fixes Made

- **Issue:** No `casino` module existed yet — `uv run pytest` failed with
  `ModuleNotFoundError: No module named 'casino'`.
  **Request:** Read `tests/test_casino.py` and the README, then implement the
  `casino` module so all the tests pass, and build a browser UI to play a full
  deal against the computer.
  **Fix:** Implemented `casino/__init__.py` (`value`, `Move`, `new_deal`,
  `legal_moves`, `play`, `deal_over`, `score`), `casino/ai.py` (a simple
  computer opponent), and `casino/server.py` (a stdlib-only HTTP server) with
  a vanilla HTML/CSS/JS UI under `casino/static/`. All 14 tests pass, and a
  full deal was played end-to-end through the real HTTP API to confirm it
  works outside of the test suite too.

- **Issue:** Clicking "Play" on a ready, legal move sometimes did nothing —
  no board update, no visible error.
  **Request:** Investigate why the Play button wasn't triggering the move.
  **Fix:** Reproduced it with a real headless-browser session. Root cause:
  a double-fired click (trackpad double-tap, or a fast repeat click) sent two
  `POST /api/move` requests. The first succeeded and changed the game state;
  the second then targeted the now-stale state and was rejected with
  `{"error": "illegal move"}`. The old client code did
  `state = await res.json()` unconditionally, so `state` became that error
  object, and the next line in `render()` (`state.sweeps.you`) threw —
  silently crashing mid-render before the hand/table redraw. Fixed in
  `casino/static/app.js`: added a `submitting` guard that disables the button
  and ignores re-entrant clicks, and routed all fetches through a `request()`
  helper that checks `res.ok`, shows a message instead of crashing on
  rejection, and re-syncs from `/api/state`.

- **Issue:** After sweeping the table, question of whether the rules cap a
  capture's total value (a 26-point combo capture — `10C+5D+JD` taking
  `KC+KH` — was rejected once).
  **Request:** Check `tests/test_casino.py` for a value cap, and explain
  exactly what makes a move legal or illegal in this implementation.
  **Fix:** No cap exists anywhere in the code or tests — confirmed by
  grepping both files and by testing the exact combo directly against
  `legal_moves()` (returned `True`). The one-off rejection was a stale
  client bug (an older copy of `app.js` in an already-open tab, before the
  Play-button fix above), not a rule. Wrote up the full rule set in plain
  language with examples from the tests: card values, placing vs. capturing
  (single-card, table-combination, and hand-combination captures), the
  "must add up exactly" and "must hold the card" illegality checks, normal
  turn alternation, the "double move" after a sweep, sweep scoring, and how
  new 3-card hands get dealt mid-deal.

- **Issue:** Reported that after a sweep, followed by both players placing
  cards (no more captures) until both hands emptied, the computer moved and
  captured immediately after the mid-deal redeal — seemingly before the
  sweeper (who should lead the new round) got a turn.
  **Request:** Check whether the code correctly tracks who made the last
  capture, since the sweeper should lead the next round.
  **Fix:** Fuzz-tested the exact scenario (force a sweep, force
  placement-only moves until both hands empty, check who leads next) across
  150+ trials. Found a real bug, but in an adjacent code path, not the one
  described: at the very end of a deal — both hands empty, stock empty, and
  cards still left on the table — those leftover cards correctly went to the
  last capturer's pile, but the code never updated whose turn it was
  afterward. Fixed in `casino/__init__.py` (the `elif table and
  last_capturer is not None` branch now also sets `next_player =
  last_capturer`). Re-ran the fuzz test after the fix: 0 failures.
  The *mid-deal* redeal path specifically described in the report (stock
  still non-empty) was tested the same way and was already correct in every
  trial — could not reproduce that exact case. Added a move-history log to
  the server (`GET /api/history`, capped at 200 entries) so any repeat of
  this report can be diagnosed from the exact move sequence instead of
  guesswork.

## Final Result

Played a full deal to completion: **14–5** (sweeps 4–3). Score check:
4 + 3 = 7 sweep points, plus 12 points from cards/majorities/aces/big-and-little
casino = 19 total across both piles, matching 14 + 5 = 19. Confirmed against
the live server's own `score()` output.
