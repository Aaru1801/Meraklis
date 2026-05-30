"""Offline smoke test for Meraklis.

Proves the system works end-to-end with **no model server** — the demo-critical
guarantee. Run after install:

    python -m openhouse.scripts.smoke_test

Exits non-zero on the first failed assertion.
"""

from __future__ import annotations

import asyncio
import sys

from openhouse.agents.edge import EdgeInvestigationRequest, get_edge_investigator
from openhouse.agents.service import get_service
from openhouse.data.store import BuildingStore

DEMO_RSN = "4154044"  # 500 Dawes Rd

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  {PASS if ok else FAIL} {label}{(' — ' + detail) if detail else ''}")
    if not ok:
        print(f"\n{FAIL} smoke test FAILED at: {label}")
        sys.exit(1)


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


async def main() -> None:
    print("\n\033[1mMeraklis — offline smoke test\033[0m")

    # --- 1. local data cache ---------------------------------------------
    section("1. Local RentSafeTO SQLite cache")
    store = BuildingStore()
    counts = store.count()
    check("buildings present", counts["buildings"] > 100, f"{counts['buildings']:,}")
    check("evaluations present", counts["evaluations"] > 100, f"{counts['evaluations']:,}")
    check("demo building resolvable", store.get_building(DEMO_RSN) is not None, DEMO_RSN)

    # --- 2. deterministic risk engine ------------------------------------
    section("2. Deterministic risk engine (no LLM)")
    svc = get_service()
    report = svc.report(DEMO_RSN)
    check("risk report built", report is not None)
    assert report is not None
    check("grade assigned", report.grade in {"A", "B", "C", "D", "F"}, f"Grade {report.grade}")
    check("composite risk in range", 0 <= report.risk_score <= 100, str(report.risk_score))
    check("red flags found", len(report.red_flags) > 0, f"{len(report.red_flags)} flags")
    check("newcomer lens present", report.newcomer_lens is not None)
    check("rights grounded", len(svc.rights(DEMO_RSN)["rights"]) > 0)

    # --- 3. full Edge investigation (batch, no model) --------------------
    section("3. Edge investigation — 8 agents, offline")
    edge = get_edge_investigator()
    result = await edge.investigate(EdgeInvestigationRequest(rsn=DEMO_RSN))
    check("address resolved", result.resolved.rsn == DEMO_RSN, result.resolved.address or "")
    check("risk attached", result.risk is not None)
    check("PIO built", result.pio is not None)
    check(
        "8 audited steps",
        len(result.audit_trail) == 8,
        f"{len(result.audit_trail)} steps",
    )
    check(
        "advocacy is deterministic fallback (no model server)",
        result.advocacy is not None and result.advocacy.generated_by == "deterministic",
    )
    check("311 draft prepared, not submitted", result.draft_311 is not None
          and result.draft_311.submit_status == "not_submitted")
    check("runtime fallback armed/used",
          "fallback" in result.runtime.fallback_status,
          result.runtime.fallback_status)

    # --- 4. evidence grounding (no hallucinated citations) ---------------
    section("4. Evidence grounding (every citation resolves)")
    evidence_ids = {e.id for e in result.evidence}
    check("evidence ledger non-empty", len(evidence_ids) > 0, f"{len(evidence_ids)} records")
    for step in result.audit_trail:
        for cit in step.citations:
            if not (cit.id in evidence_ids or cit.id.startswith(("pio:", "rights:"))):
                check(f"citation {cit.id} grounded", False, step.agent)
    check("all step citations resolve to evidence", True)
    if result.draft_311:
        ok = all(eid in evidence_ids for eid in result.draft_311.evidence_ids)
        check("311 draft cites only real evidence", ok)

    # --- 5. streaming pipeline emits the right events --------------------
    section("5. Streaming pipeline events")
    seen_types: list[str] = []
    n_done = 0
    async for event in edge.run(EdgeInvestigationRequest(rsn=DEMO_RSN), pace=False):
        seen_types.append(event["type"])
        if event["type"] == "agent_done":
            n_done += 1
    check("pipeline skeleton emitted first", seen_types[0] == "pipeline", seen_types[0])
    check("8 agent_done events", n_done == 8, f"{n_done}")
    check("runtime event emitted", "runtime" in seen_types)
    check("result event emitted last", seen_types[-1] == "result", seen_types[-1])

    # --- 6. 3D Massing enrichment (offline, from cache) ------------------
    section("6. 3D Massing enrichment (cache-based, offline)")
    massing = result.pio.massing if result.pio else None
    if massing and massing.matched:
        check("3D Massing footprint matched", massing.matched)
        check("footprint geometry cached", len(massing.footprint_m) >= 3,
              f"{len(massing.footprint_m)} verts")
        check("roof height present", (massing.max_height_m or 0) > 0, f"{massing.max_height_m} m")
        check("height cross-check computed", massing.cross_check is not None
              and massing.cross_check.status in {"consistent", "differs", "unknown"},
              massing.cross_check.status if massing.cross_check else "none")
        # The crucial guarantee: massing must NOT change the deterministic risk score.
        check(
            "massing does NOT affect the risk score",
            result.risk.risk_score == report.risk_score,
            f"risk_score={result.risk.risk_score}",
        )
    else:
        check("3D Massing cache present (run ingest_massing)", False,
              "no massing_cache.json — optional, but expected for demo buildings")

    store.close()
    print(f"\n{PASS} \033[1mAll checks passed — Meraklis runs fully offline.\033[0m\n")


if __name__ == "__main__":
    asyncio.run(main())
