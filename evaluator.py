import logging
import time
from typing import Dict, Any

import chess
import chess.engine

from .config import ENGINE_PATH, DEFAULT_TIME_MS, STOCKFISH_CONFIG


logger = logging.getLogger("engine")

# ==================================================
# GLOBAL ENGINE INSTANCE (INTENTIONALLY RESETTABLE)
# ==================================================

_engine: chess.engine.SimpleEngine | None = None


# ==================================================
# ENGINE LIFECYCLE (LOW LEVEL)
# ==================================================

def _warmup_engine(engine: chess.engine.SimpleEngine):
    """
    Warm-up Stockfish after spawn.
    REQUIRED on Windows to avoid access violation / crash loop.
    """
    time.sleep(0.3)  # critical on Windows

    try:
        engine.analyse(
            chess.Board(),
            chess.engine.Limit(time=0.01)
        )
    except Exception:
        # warm-up failure is non-fatal
        pass


def _spawn_engine() -> chess.engine.SimpleEngine:
    logger.warning("ENGINE: spawning new Stockfish process")

    engine = chess.engine.SimpleEngine.popen_uci(str(ENGINE_PATH))
    engine.configure(STOCKFISH_CONFIG)

    _warmup_engine(engine)

    return engine


def _hard_reset_engine(reason: str):
    """
    HARD RESET.
    ANY protocol corruption => kill engine, drop reference.
    """
    global _engine

    logger.error("ENGINE HARD RESET: %s", reason)

    if _engine is not None:
        try:
            _engine.quit()
        except Exception:
            pass

    _engine = None


def _get_engine() -> chess.engine.SimpleEngine:
    global _engine

    if _engine is None:
        _engine = _spawn_engine()

    return _engine


def close_engine():
    _hard_reset_engine("manual close")


# ==================================================
# PUBLIC API (STRICT CONTRACT)
# ==================================================

def evaluate_position(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyse a chess position.

    INPUT:
    {
        "fen": "<FULL_FEN_6_FIELD>",
        "time_ms": <INT>
    }

    OUTPUT (ALWAYS SAME STRUCTURE):
    {
        "eval": {
            "type": "cp" | "mate",
            "value": <INT | None>
        },
        "best_move_uci": "<UCI_MOVE>" | None,
        "ok": <bool>
    }
    """

    # ---------------------------
    # Validate input
    # ---------------------------

    fen = input_data.get("fen")
    time_ms = input_data.get("time_ms", DEFAULT_TIME_MS)

    if not isinstance(fen, str):
        raise ValueError("fen must be a string")

    if not isinstance(time_ms, int) or time_ms <= 0:
        raise ValueError("time_ms must be a positive integer")

    board = chess.Board(fen)
    side_to_move = board.turn
    limit = chess.engine.Limit(time=time_ms / 1000)

    # ---------------------------
    # Analyse (CRITICAL SECTION)
    # ---------------------------

    try:
        engine = _get_engine()
        info = engine.analyse(board, limit)

        pv = info.get("pv")
        best_move_uci = pv[0].uci() if pv else None

        score = info["score"].pov(side_to_move)

        if score.is_mate():
            return {
                "eval": {
                    "type": "mate",
                    "value": score.mate()
                },
                "best_move_uci": best_move_uci,
                "ok": True
            }

        return {
            "eval": {
                "type": "cp",
                "value": score.score()
            },
            "best_move_uci": best_move_uci,
            "ok": True
        }

    except Exception as e:
        # ---------------------------------
        # ANY ERROR = ENGINE IS DEAD
        # ---------------------------------
        logger.exception("ENGINE analyse failed")

        _hard_reset_engine(type(e).__name__)

        # IMPORTANT:
        # ❌ DO NOT retry analyse here
        # Next analyse must be a NEW job from main

        return {
            "eval": {
                "type": "cp",
                "value": None
            },
            "best_move_uci": None,
            "ok": False
        }


# ==================================================
# LOCAL DEBUG (OPTIONAL)
# ==================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_input = {
        "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
        "time_ms": 100
    }

    print(evaluate_position(test_input))
