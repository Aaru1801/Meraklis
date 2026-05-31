"""Tenant-reported building conditions — a SEPARATE store from the official
RentSafeTO data.

User-submitted photo evidence never mutates the City's authoritative inspection
scores. Instead, each verified condition contributes a signed delta, and the
"live" score is computed on read as ``clamp(official_score + sum(deltas), 0, 100)``.
This keeps the official baseline pristine and the community layer transparent.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .store import DEFAULT_DB_PATH

# Kept alongside the canonical DB but in its OWN file, so the official data is
# never touched by community submissions.
_DB_PATH = DEFAULT_DB_PATH.parent / "conditions.sqlite3"
_COLS = ("id", "rsn", "created_at", "kind", "label", "severity", "delta", "explanation", "model")


def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS condition_reports ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, rsn TEXT NOT NULL, created_at TEXT NOT NULL, "
        "kind TEXT NOT NULL, label TEXT, severity TEXT, delta INTEGER NOT NULL, "
        "explanation TEXT, model TEXT)"
    )
    return conn


def add_report(
    *, rsn: str, kind: str, label: str, severity: str, delta: int, explanation: str, model: str
) -> dict:
    """Persist one tenant-reported condition and return it."""
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO condition_reports "
            "(rsn, created_at, kind, label, severity, delta, explanation, model) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (rsn, created, kind, label, severity, int(delta), explanation, model),
        )
        rid = cur.lastrowid
    return {
        "id": rid, "rsn": rsn, "created_at": created, "kind": kind, "label": label,
        "severity": severity, "delta": int(delta), "explanation": explanation, "model": model,
    }


def reports_for(rsn: str) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, rsn, created_at, kind, label, severity, delta, explanation, model "
            "FROM condition_reports WHERE rsn = ? ORDER BY id DESC",
            (rsn,),
        ).fetchall()
    return [dict(zip(_COLS, r)) for r in rows]


def summary(rsn: str, base_score: int | None) -> dict:
    """Official baseline + the live (community-adjusted) score for a building."""
    reports = reports_for(rsn)
    delta_total = sum(int(r["delta"]) for r in reports)
    live = max(0, min(100, int(base_score) + delta_total)) if base_score is not None else None
    return {
        "rsn": rsn,
        "base_score": base_score,
        "delta_total": delta_total,
        "live_score": live,
        "n_reports": len(reports),
        "reports": reports,
    }
