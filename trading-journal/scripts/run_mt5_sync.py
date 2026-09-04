"""Triggered by the journal's "Sync MT5" button.

Runs the actual MT5 pull (fetch + POST to /api/sync). Kept separate so the
web UI can call it without holding MetaTrader5 in-process.
"""

import sys
import subprocess
from pathlib import Path

MT5_SYNC = Path(__file__).resolve().parent / "mt5_sync.py"
PYTHON = sys.executable


def run(days: int = 90) -> tuple[int, str]:
    cmd = [PYTHON, str(MT5_SYNC), "--days", str(days)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        out = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, out.strip()
    except subprocess.TimeoutExpired:
        return 1, "timeout 120s"
    except Exception as e:
        return 1, str(e)
