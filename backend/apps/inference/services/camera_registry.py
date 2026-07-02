from __future__ import annotations

import threading

from .session_manager import SessionManager

MAX_SLOTS = 4

_sessions: dict[int, SessionManager] = {}
_lock = threading.Lock()


def get_session(slot: int = 0) -> SessionManager:
    slot = max(0, min(MAX_SLOTS - 1, int(slot)))
    if slot not in _sessions:
        with _lock:
            if slot not in _sessions:
                _sessions[slot] = SessionManager()
    return _sessions[slot]
