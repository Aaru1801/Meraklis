"""SQLite-backed store for RentSafeTO evaluations.

Two tables:

* ``evaluations`` — one row per evaluation (every RSN × year), with the raw
  per-category scores kept as JSON. This is the source of truth and powers
  per-building history and trends.
* ``buildings`` — a denormalized snapshot of the *latest* evaluation per RSN,
  for fast search, map rendering and neighbourhood aggregates.

The store is deliberately dependency-free (stdlib ``sqlite3``) so the data
layer runs anywhere, with or without the agent/LLM stack.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from .models import Building, BuildingSummary, Evaluation

log = logging.getLogger("openhouse.store")

DEFAULT_DB_PATH = Path(
    os.environ.get(
        "OPENHOUSE_DB_PATH",
        str(Path(__file__).resolve().parents[3] / "data" / "rentsafeto.sqlite3"),
    )
)


def _norm(text: str | None) -> str:
    return " ".join((text or "").lower().split())


class BuildingStore:
    """Thin, synchronous SQLite wrapper around the evaluation dataset."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError as exc:
            log.warning("SQLite WAL mode unavailable for %s: %s", self.db_path, exc)
        self._init_schema()

    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rsn TEXT NOT NULL,
                address TEXT,
                ward TEXT,
                ward_name TEXT,
                property_type TEXT,
                year_built INTEGER,
                year_registered INTEGER,
                year_evaluated INTEGER,
                completed_on TEXT,
                storeys INTEGER,
                units INTEGER,
                score INTEGER,
                proactive_score INTEGER,
                reactive_score INTEGER,
                areas_evaluated INTEGER,
                latitude REAL,
                longitude REAL,
                categories_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_eval_rsn ON evaluations(rsn);

            CREATE TABLE IF NOT EXISTS buildings (
                rsn TEXT PRIMARY KEY,
                address TEXT,
                address_norm TEXT,
                ward TEXT,
                ward_name TEXT,
                latitude REAL,
                longitude REAL,
                storeys INTEGER,
                units INTEGER,
                year_built INTEGER,
                score INTEGER,
                proactive_score INTEGER,
                reactive_score INTEGER,
                completed_on TEXT,
                score_trend INTEGER,
                n_evals INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_bldg_addr ON buildings(address_norm);
            CREATE INDEX IF NOT EXISTS idx_bldg_ward ON buildings(ward_name);
            CREATE INDEX IF NOT EXISTS idx_bldg_score ON buildings(score);
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------
    def ingest(self, evaluations: Iterable[Evaluation]) -> dict[str, int]:
        """Replace the dataset with ``evaluations`` and rebuild the snapshot."""
        evals = list(evaluations)
        cur = self._conn.cursor()
        cur.execute("DELETE FROM evaluations")
        cur.execute("DELETE FROM buildings")

        cur.executemany(
            """
            INSERT INTO evaluations (
                rsn, address, ward, ward_name, property_type,
                year_built, year_registered, year_evaluated, completed_on,
                storeys, units, score, proactive_score, reactive_score,
                areas_evaluated, latitude, longitude, categories_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            [
                (
                    e.rsn, e.address, e.ward, e.ward_name, e.property_type,
                    e.year_built, e.year_registered, e.year_evaluated,
                    e.evaluation_completed_on.isoformat() if e.evaluation_completed_on else None,
                    e.storeys, e.units, e.score, e.proactive_score, e.reactive_score,
                    e.areas_evaluated, e.latitude, e.longitude,
                    json.dumps(e.categories),
                )
                for e in evals
            ],
        )

        # Build the per-RSN snapshot from the just-inserted rows.
        by_rsn: dict[str, list[Evaluation]] = {}
        for e in evals:
            by_rsn.setdefault(e.rsn, []).append(e)

        snapshot_rows = []
        for rsn, group in by_rsn.items():
            bldg = Building.from_evaluations(group)
            c = bldg.current
            snapshot_rows.append(
                (
                    rsn, bldg.address, _norm(bldg.address), bldg.ward, bldg.ward_name,
                    bldg.latitude, bldg.longitude, bldg.storeys, bldg.units, bldg.year_built,
                    c.score, c.proactive_score, c.reactive_score,
                    c.evaluation_completed_on.isoformat() if c.evaluation_completed_on else None,
                    bldg.score_trend, len(group),
                )
            )
        cur.executemany(
            """
            INSERT OR REPLACE INTO buildings (
                rsn, address, address_norm, ward, ward_name, latitude, longitude,
                storeys, units, year_built, score, proactive_score, reactive_score,
                completed_on, score_trend, n_evals
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            snapshot_rows,
        )
        self._conn.commit()
        stats = {"evaluations": len(evals), "buildings": len(by_rsn)}
        log.info("ingested %s", stats)
        return stats

    # ------------------------------------------------------------------
    # Reconstruction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_eval(row: sqlite3.Row) -> Evaluation:
        import datetime as dt

        cats = json.loads(row["categories_json"] or "{}")
        completed = None
        if row["completed_on"]:
            try:
                completed = dt.date.fromisoformat(row["completed_on"])
            except ValueError:
                completed = None
        return Evaluation(
            rsn=row["rsn"], address=row["address"] or "",
            ward=row["ward"], ward_name=row["ward_name"], property_type=row["property_type"],
            year_built=row["year_built"], year_registered=row["year_registered"],
            year_evaluated=row["year_evaluated"], evaluation_completed_on=completed,
            storeys=row["storeys"], units=row["units"],
            score=row["score"], proactive_score=row["proactive_score"],
            reactive_score=row["reactive_score"], areas_evaluated=row["areas_evaluated"],
            latitude=row["latitude"], longitude=row["longitude"], categories=cats,
        )

    @staticmethod
    def _row_to_summary(row: sqlite3.Row) -> BuildingSummary:
        return BuildingSummary(
            rsn=row["rsn"], address=row["address"], ward_name=row["ward_name"],
            latitude=row["latitude"], longitude=row["longitude"],
            units=row["units"], storeys=row["storeys"], year_built=row["year_built"],
            score=row["score"],
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def get_building(self, rsn: str) -> Building | None:
        rows = self._conn.execute(
            "SELECT * FROM evaluations WHERE rsn = ?", (rsn,)
        ).fetchall()
        if not rows:
            return None
        evals = [self._row_to_eval(r) for r in rows]
        return Building.from_evaluations(evals)

    def search(self, query: str, limit: int = 25) -> list[BuildingSummary]:
        q = _norm(query)
        if not q:
            return []
        rows = self._conn.execute(
            """
            SELECT * FROM buildings
            WHERE address_norm LIKE ? OR lower(ward_name) LIKE ?
            ORDER BY (address_norm = ?) DESC, score ASC
            LIMIT ?
            """,
            (f"%{q}%", f"%{q}%", q, limit),
        ).fetchall()
        return [self._row_to_summary(r) for r in rows]

    def map_points(
        self,
        limit: int = 5000,
        max_score: int | None = None,
        min_score: int | None = None,
        ward_name: str | None = None,
    ) -> list[BuildingSummary]:
        clauses = ["latitude IS NOT NULL", "longitude IS NOT NULL"]
        params: list[object] = []
        if max_score is not None:
            clauses.append("score <= ?")
            params.append(max_score)
        if min_score is not None:
            clauses.append("score >= ?")
            params.append(min_score)
        if ward_name:
            clauses.append("lower(ward_name) = ?")
            params.append(ward_name.lower())
        params.append(limit)
        rows = self._conn.execute(
            f"SELECT * FROM buildings WHERE {' AND '.join(clauses)} "
            f"ORDER BY score ASC LIMIT ?",
            params,
        ).fetchall()
        return [self._row_to_summary(r) for r in rows]

    def worst(self, limit: int = 10, ward_name: str | None = None) -> list[BuildingSummary]:
        params: list[object] = []
        where = "score IS NOT NULL"
        if ward_name:
            where += " AND lower(ward_name) = ?"
            params.append(ward_name.lower())
        params.append(limit)
        rows = self._conn.execute(
            f"SELECT * FROM buildings WHERE {where} ORDER BY score ASC LIMIT ?", params
        ).fetchall()
        return [self._row_to_summary(r) for r in rows]

    def neighbourhood_stats(self, ward_name: str) -> dict[str, object]:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n, AVG(score) AS avg_score,
                   MIN(score) AS min_score, MAX(score) AS max_score,
                   SUM(CASE WHEN score < 65 THEN 1 ELSE 0 END) AS n_high_risk
            FROM buildings WHERE lower(ward_name) = ? AND score IS NOT NULL
            """,
            (ward_name.lower(),),
        ).fetchone()
        return {
            "ward_name": ward_name,
            "n_buildings": row["n"],
            "avg_score": round(row["avg_score"], 1) if row["avg_score"] is not None else None,
            "min_score": row["min_score"],
            "max_score": row["max_score"],
            "n_high_risk": row["n_high_risk"],
        }

    def list_wards(self) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT ward_name, COUNT(*) AS n, ROUND(AVG(score), 1) AS avg_score
            FROM buildings WHERE ward_name IS NOT NULL AND score IS NOT NULL
            GROUP BY ward_name ORDER BY ward_name
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def city_stats(self) -> dict[str, object]:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS n_buildings, ROUND(AVG(score),1) AS avg_score,
                   SUM(units) AS total_units,
                   SUM(CASE WHEN score < 65 THEN 1 ELSE 0 END) AS n_high_risk
            FROM buildings WHERE score IS NOT NULL
            """
        ).fetchone()
        n_evals = self._conn.execute("SELECT COUNT(*) AS n FROM evaluations").fetchone()["n"]
        return {**dict(row), "n_evaluations": n_evals}

    def count(self) -> dict[str, int]:
        b = self._conn.execute("SELECT COUNT(*) AS n FROM buildings").fetchone()["n"]
        e = self._conn.execute("SELECT COUNT(*) AS n FROM evaluations").fetchone()["n"]
        return {"buildings": b, "evaluations": e}

    def close(self) -> None:
        self._conn.close()
