"""A small stdlib-only web server for playing Cassino against the computer.

Run with: uv run python -m casino.server
Then open http://localhost:8000/
"""
import json
import random
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import Move, deal_over, legal_moves, new_deal, play, score
from .ai import choose_move

STATIC_DIR = Path(__file__).parent / "static"
HUMAN, COMPUTER = 0, 1

_lock = threading.Lock()
_state = None
_message = ""
_history = []


def _record(mover, move):
    """Keep a short log of moves for diagnosing turn-order reports."""
    _history.append({
        "player": "you" if mover == HUMAN else "computer",
        "played": sorted(move.hand),
        "took": sorted(move.table),
        "sweep": bool(move.table) and not _state.table,
        "handsAfter": {"you": len(_state.hands[HUMAN]), "computer": len(_state.hands[COMPUTER])},
        "talonAfter": len(_state.talon),
        "playerAfter": "you" if _state.player == HUMAN else "computer",
        "lastCapturer": "you" if _state.last_capturer == HUMAN
                        else ("computer" if _state.last_capturer == COMPUTER else None),
    })
    del _history[:-200]


def _shuffled_deck():
    ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    cards = [r + s for s in "SHDC" for r in ranks]
    random.shuffle(cards)
    return cards


def _new_game():
    global _state, _message, _history
    _state = new_deal(_shuffled_deck(), first=random.randint(0, 1))
    _history = []
    _message = "Computer deals. Your turn." if _state.player == HUMAN else "Computer deals and leads."
    _run_computer()


def _run_computer():
    """Let the computer play moves until it's the human's turn or the deal is over."""
    global _state, _message
    while not deal_over(_state) and _state.player == COMPUTER:
        move = choose_move(_state)
        _state = play(_state, move)
        _record(COMPUTER, move)
    if deal_over(_state):
        p0, p1 = score(_state)
        if p0 > p1:
            _message = f"Deal over. You win {p0}-{p1}!"
        elif p1 > p0:
            _message = f"Deal over. Computer wins {p1}-{p0}."
        else:
            _message = f"Deal over. It's a tie, {p0}-{p1}."


def _move_view(move):
    return {"hand": sorted(move.hand), "table": sorted(move.table)}


def _state_view():
    over = deal_over(_state)
    moves = []
    if not over and _state.player == HUMAN:
        moves = [_move_view(m) for m in legal_moves(_state)]
    view = {
        "hand": sorted(_state.hands[HUMAN]),
        "computerCount": len(_state.hands[COMPUTER]),
        "computerHand": sorted(_state.hands[COMPUTER]) if over else None,
        "table": sorted(_state.table),
        "talonCount": len(_state.talon),
        "piles": {
            "you": sorted(_state.piles[HUMAN]),
            "computer": sorted(_state.piles[COMPUTER]),
        },
        "sweeps": {"you": _state.sweeps[HUMAN], "computer": _state.sweeps[COMPUTER]},
        "yourTurn": (not over) and _state.player == HUMAN,
        "dealOver": over,
        "moves": moves,
        "message": _message,
    }
    if over:
        p_you, p_comp = score(_state)
        view["score"] = {"you": p_you, "computer": p_comp}
    return view


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path):
        if path == "/":
            path = "/index.html"
        file_path = (STATIC_DIR / path.lstrip("/")).resolve()
        if STATIC_DIR not in file_path.parents and file_path != STATIC_DIR:
            self.send_error(404)
            return
        if not file_path.is_file():
            self.send_error(404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            with _lock:
                self._send_json(_state_view())
            return
        if self.path == "/api/history":
            with _lock:
                self._send_json({"history": _history})
            return
        self._send_static(self.path)

    def do_POST(self):
        global _state, _message
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            data = {}

        if self.path == "/api/new":
            with _lock:
                _new_game()
                self._send_json(_state_view())
            return

        if self.path == "/api/move":
            with _lock:
                if _state is None or deal_over(_state) or _state.player != HUMAN:
                    self._send_json({"error": "not your turn"}, status=400)
                    return
                move = Move(frozenset(data.get("hand", [])), frozenset(data.get("table", [])))
                if move not in legal_moves(_state):
                    self._send_json({"error": "illegal move"}, status=400)
                    return
                _state = play(_state, move)
                _record(HUMAN, move)
                _message = ""
                _run_computer()
                self._send_json(_state_view())
            return

        self.send_error(404)


def main():
    with _lock:
        _new_game()
    server = ThreadingHTTPServer(("localhost", 8000), Handler)
    url = "http://localhost:8000/"
    print(f"Cassino running at {url}")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
