"""Operator / portfolio queries over the ``building_operators`` table.

These power the Operator/Portfolio agent's real (not punted) analysis: given a
set of raw operator spellings that the resolver has decided denote ONE company,
pull every building under them and find the inspection categories that 2+ of
those buildings fail — the "shared neglect" pattern the public city site can't
show (it only shows one building at a time).

Pure stdlib sqlite, read-only. Degrades gracefully (empty results) if the
``building_operators`` table is absent (i.e. ingest_operators was never run).

Domain rule (matches the dataset's 0–3 category grades): a category is *failed*
at score ≤ 1, and a 0 (a required document/plan entirely absent) is worse than 1.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache

from .store import DEFAULT_DB_PATH


@dataclass(frozen=True, slots=True)
class OpBuilding:
    rsn: str
    address: str | None
    ward_name: str | None
    score: int | None
    latitude: float | None
    longitude: float | None


@dataclass(slots=True)
class SharedFailure:
    category: str
    buildings: int  # distinct buildings failing this category (score ≤ 1)
    count0: int     # buildings scoring 0 (required doc absent — worst)
    count1: int     # buildings scoring 1
    severity: int   # ranking weight: 0s weighted above 1s


@lru_cache(maxsize=1)
def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DEFAULT_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _has_operator_table() -> bool:
    row = _conn().execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='building_operators'"
    ).fetchone()
    return row is not None


def operator_raw_for(rsn: str) -> str | None:
    """The raw operator spelling registered for a building, or None."""
    if not _has_operator_table():
        return None
    row = _conn().execute(
        "SELECT operator_raw FROM building_operators WHERE rsn = ?", (rsn,)
    ).fetchone()
    name = (row["operator_raw"].strip() if row and row["operator_raw"] else "")
    return name or None


def distinct_operator_raws() -> list[str]:
    """Every distinct non-blank operator spelling — the entity-resolution universe."""
    if not _has_operator_table():
        return []
    return [
        r["operator_raw"]
        for r in _conn().execute(
            "SELECT DISTINCT operator_raw FROM building_operators "
            "WHERE TRIM(operator_raw) <> '' ORDER BY operator_raw"
        )
    ]


def buildings_by_operator_raws(members: list[str]) -> list[OpBuilding]:
    """All buildings whose operator matches any of the given raw spellings."""
    names = [m.strip() for m in members if m and m.strip()]
    if not names or not _has_operator_table():
        return []
    ph = ",".join("?" * len(names))
    rows = _conn().execute(
        f"""
        SELECT b.rsn, b.address, b.ward_name, b.score, b.latitude, b.longitude
        FROM buildings b JOIN building_operators o ON o.rsn = b.rsn
        WHERE o.operator_raw IN ({ph})
        ORDER BY b.score ASC
        """,
        names,
    ).fetchall()
    return [
        OpBuilding(
            rsn=r["rsn"], address=r["address"], ward_name=r["ward_name"],
            score=r["score"], latitude=r["latitude"], longitude=r["longitude"],
        )
        for r in rows
    ]


def latest_categories(rsn: str) -> dict[str, int]:
    """Category → score for a building's most recent evaluation (skips N/A)."""
    row = _conn().execute(
        """
        SELECT categories_json FROM evaluations WHERE rsn = ?
        ORDER BY year_evaluated DESC, completed_on DESC LIMIT 1
        """,
        (rsn,),
    ).fetchone()
    if not row or not row["categories_json"]:
        return {}
    out: dict[str, int] = {}
    for cat, score in json.loads(row["categories_json"]).items():
        if isinstance(score, (int, float)):
            out[cat] = int(score)
    return out


def failing_categories(rsn: str) -> dict[str, int]:
    """Just the failed (score ≤ 1) categories of a building's latest eval."""
    return {c: s for c, s in latest_categories(rsn).items() if s <= 1}


def shared_failures(rsns: list[str]) -> list[SharedFailure]:
    """Categories that 2+ of the given buildings fail, ranked worst-first.

    Worst-first = most 0s (required doc absent), then most 1s, then severity.
    """
    uniq = list(dict.fromkeys(r for r in rsns if r))
    count0: dict[str, int] = {}
    count1: dict[str, int] = {}
    for rsn in uniq:
        for cat, score in failing_categories(rsn).items():
            if score == 0:
                count0[cat] = count0.get(cat, 0) + 1
            else:
                count1[cat] = count1.get(cat, 0) + 1

    out: list[SharedFailure] = []
    for cat in set(count0) | set(count1):
        c0, c1 = count0.get(cat, 0), count1.get(cat, 0)
        if c0 + c1 < 2:  # "shared" needs 2+ buildings
            continue
        out.append(SharedFailure(cat, c0 + c1, c0, c1, c0 * 2 + c1))
    out.sort(key=lambda f: (-f.count0, -f.count1, -f.severity, f.category))
    return out


def portfolio_failures(
    rsns: list[str],
) -> tuple[list[SharedFailure], dict[str, dict[str, int]]]:
    """Shared failures AND each building's failing shared categories, in one pass.

    Reads every building's latest eval exactly once (a big portfolio like TCH is
    hundreds of buildings), so callers don't re-query per building.
    """
    uniq = list(dict.fromkeys(r for r in rsns if r))
    failing_all = {r: failing_categories(r) for r in uniq}

    count0: dict[str, int] = {}
    count1: dict[str, int] = {}
    for cats in failing_all.values():
        for cat, score in cats.items():
            if score == 0:
                count0[cat] = count0.get(cat, 0) + 1
            else:
                count1[cat] = count1.get(cat, 0) + 1

    shared: list[SharedFailure] = []
    for cat in set(count0) | set(count1):
        c0, c1 = count0.get(cat, 0), count1.get(cat, 0)
        if c0 + c1 < 2:
            continue
        shared.append(SharedFailure(cat, c0 + c1, c0, c1, c0 * 2 + c1))
    shared.sort(key=lambda f: (-f.count0, -f.count1, -f.severity, f.category))

    shared_set = {f.category for f in shared}
    failing_by_rsn = {
        r: {c: s for c, s in cats.items() if c in shared_set} for r, cats in failing_all.items()
    }
    return shared, failing_by_rsn
