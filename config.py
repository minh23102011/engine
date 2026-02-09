from pathlib import Path

ENGINE_PATH = Path(__file__).parent / "stockfish-windows-x86-64-avx2.exe"

DEFAULT_TIME_MS = 100

STOCKFISH_CONFIG = {
    # Strength
    "Skill Level": 20,

    # Performance
    "Threads": 6,
    "Hash": 512,

    # Analysis
    "Move Overhead": 30,

    # Tablebase (optional)
    "SyzygyPath": "",
    "SyzygyProbeDepth": 1,
    "Syzygy50MoveRule": True,
}
# ===============================
# ANALYSIS STAGES (MAIN CONTRACT)
# ===============================

# thời gian phân tích cho mỗi nước (ms)
ANALYSIS_STAGES_MS = [300, 1500, 5000]
