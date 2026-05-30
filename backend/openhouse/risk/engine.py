"""Deterministic risk engine.

Turns a :class:`~openhouse.data.models.Building` into a structured
:class:`~openhouse.risk.report.RiskReport`. Everything here is pure, explainable
arithmetic over the City's published data — no LLM, no network. The agents layer
*reasoning and advice* on top of this; they never invent the underlying facts.

Design choices:
* The City's official 0-100 evaluation score anchors the grade — it's their
  audited methodology and the most defensible single number.
* On top of that we surface *which* deficiencies drive the score and weight the
  ones that matter most for safety, health and (especially) newcomers.
* A composite ``risk_score`` lets a mediocre building with severe safety flags
  rank as riskier than a slightly-lower-scored building that's merely tired.
"""

from __future__ import annotations

import datetime as dt

from ..data.categories import BY_KEY, Group
from ..data.models import Building, CategoryScore
from .report import (
    GroupScore,
    NewcomerLens,
    RedFlag,
    RiskReport,
    Severity,
    Strength,
    TrendInfo,
)

# Management/record-keeping categories with legal relevance (record-keeping is
# required under Toronto's RentSafeTO bylaw; gaps weaken a tenant's later case).
RECORD_KEYS = (
    "VITAL SERVICE PLAN",
    "ELECTRICAL SAFETY PLAN",
    "STATE OF GOOD REPAIR PLAN",
    "MAINTENANCE LOG",
    "CLEANING LOG",
    "PEST CONTROL LOG",
    "TENANT SERVICE REQUEST LOG",
)

# Plain-language questions a renter should ask, keyed by the category that
# triggers them. Surfaced in the newcomer lens.
QUESTION_BY_KEY: dict[str, str] = {
    "COMMON AREA PESTS": "Ask to see the building's pest-control log and the date of the last treatment — and check unit corners and kitchens during your viewing.",
    "PEST CONTROL LOG": "Ask whether the building has a scheduled, documented pest-control program and request to see recent records.",
    "EXTERIOR DOORS": "Test the main entrance lock during your viewing and ask how quickly broken door hardware gets fixed.",
    "INTERCOM": "Confirm the intercom/buzzer works and ask how guests and deliveries are let in.",
    "VITAL SERVICE PLAN": "Ask how fast heat and hot water are restored when they fail, and who you call after hours and on weekends.",
    "WINDOWS": "Check windows for drafts and ask about typical winter heating costs.",
    "MAINTENANCE LOG": "Ask exactly how you submit a repair request and how it's tracked — request a recent example.",
    "TENANT SERVICE REQUEST LOG": "Ask to see how tenant service requests are logged so you'll have a paper trail if a repair is ignored.",
    "ELEVATOR MAINTENANCE": "If you'd live on an upper floor, ask how often the elevators are out of service.",
    "STAIRWELL LIGHTING": "Walk the stairwells and check the lighting — burnt-out lights signal slow maintenance.",
    "BALCONY GUARDS": "If there's a balcony, check that the railings are solid — important with young children.",
    "ELECTRICAL SERVICES / OUTLETS": "Ask when common-area electrical systems were last inspected.",
    "EXTERIOR WALKWAYS": "Ask how walkways and entrances are cleared of snow and ice in winter.",
    "MAIL RECEPTACLES": "Check that mailboxes lock securely — important for protecting government and immigration mail.",
}


def grade_for(score: int | None) -> str:
    if score is None:
        return "N/A"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _level_for(risk_score: int) -> str:
    if risk_score < 15:
        return "Low"
    if risk_score < 35:
        return "Moderate"
    if risk_score < 55:
        return "Elevated"
    if risk_score < 75:
        return "High"
    return "Severe"


def _severity_for_poor(weight: int, newcomer: bool) -> Severity:
    if weight >= 5:
        return Severity.CRITICAL if newcomer else Severity.HIGH
    if weight == 4:
        return Severity.HIGH if newcomer else Severity.MODERATE
    if weight == 3:
        return Severity.MODERATE if newcomer else Severity.MINOR
    return Severity.MINOR


def _round_or_none(value: float | None) -> int | None:
    return int(round(value)) if value is not None else None


class RiskEngine:
    """Stateless assessor. Construct once, call :meth:`assess` per building."""

    def __init__(self, today: dt.date | None = None):
        self.today = today or dt.date.today()

    # ------------------------------------------------------------------
    def assess(self, building: Building) -> RiskReport:
        ev = building.current
        cats = ev.category_scores()
        by_key = {c.key: c for c in cats}

        report = RiskReport(
            rsn=building.rsn,
            address=building.address,
            ward_name=building.ward_name,
            latitude=building.latitude,
            longitude=building.longitude,
            units=building.units,
            storeys=building.storeys,
            year_built=building.year_built,
            property_type=ev.property_type,
            overall_score=ev.score,
            grade=grade_for(ev.score),
            evaluation_date=ev.evaluation_completed_on,
            n_evaluations=1 + len(building.history),
        )

        # --- red flags from poor categories -------------------------------
        red_flags: list[RedFlag] = []
        not_assessed: list[RedFlag] = []
        for c in cats:
            if c.is_poor:
                red_flags.append(
                    RedFlag(
                        code=f"poor:{c.key}",
                        title=f"{c.label}: poor condition",
                        detail=c.tenant_impact,
                        severity=_severity_for_poor(c.weight, c.newcomer_critical),
                        group=c.group,
                        newcomer_relevant=c.newcomer_critical,
                        category_key=c.key,
                        score=1,
                        evidence="Scored 1 of 3 ('poor') at the last City inspection.",
                    )
                )
            elif c.is_not_assessed:
                not_assessed.append(
                    RedFlag(
                        code=f"obstructed:{c.key}",
                        title=f"{c.label}: could not be inspected",
                        detail=(
                            f"{c.tenant_impact} The inspector could not assess this area — "
                            "usually because access was obstructed or refused, which is itself "
                            "worth asking about."
                        ),
                        severity=Severity.MINOR if c.weight >= 4 else Severity.INFO,
                        group=c.group,
                        newcomer_relevant=c.newcomer_critical,
                        category_key=c.key,
                        score=0,
                        evidence="Recorded as 0 ('obstructed / refused') at inspection.",
                    )
                )

        # --- derived flags ------------------------------------------------
        red_flags.extend(self._derived_flags(building, by_key))

        red_flags.sort(key=lambda f: (-f.severity.rank, 0 if f.newcomer_relevant else 1, f.title))
        report.red_flags = red_flags
        report.not_assessed = not_assessed

        # --- group breakdown ----------------------------------------------
        report.group_breakdown = self._group_breakdown(cats)

        # --- strengths ----------------------------------------------------
        report.strengths = self._strengths(cats, building)

        # --- trend --------------------------------------------------------
        report.trend = self._trend(building)

        # --- composite risk score & level --------------------------------
        report.risk_score = self._composite_risk(ev.score, red_flags, building, report.trend)
        report.risk_level = _level_for(report.risk_score)

        # --- newcomer lens ------------------------------------------------
        report.newcomer_lens = self._newcomer_lens(report.risk_score, red_flags)

        # --- headline + summary ------------------------------------------
        report.headline_factors = self._headline_factors(report)
        report.summary_line = self._summary_line(report)

        return report

    # ------------------------------------------------------------------
    def _derived_flags(self, building: Building, by_key: dict[str, CategoryScore]) -> list[RedFlag]:
        ev = building.current
        flags: list[RedFlag] = []

        if ev.has_reactive_issues:
            flags.append(
                RedFlag(
                    code="derived:reactive",
                    title="Open work orders or complaints on file",
                    detail=(
                        "The building carries a non-zero reactive score, meaning the City has "
                        "recorded outstanding work orders or tenant complaints that required "
                        "follow-up enforcement — a sign issues aren't resolved proactively."
                    ),
                    severity=Severity.HIGH,
                    newcomer_relevant=True,
                    evidence=f"Reactive score: {ev.reactive_score}.",
                )
            )

        # Missing management/record-keeping (aggregate signal).
        missing = [
            by_key[k].label for k in RECORD_KEYS if k in by_key and by_key[k].is_poor
        ]
        if len(missing) >= 2:
            flags.append(
                RedFlag(
                    code="derived:records",
                    title="Required management records are missing or poor",
                    detail=(
                        "The building scored poorly on multiple legally-relevant records ("
                        + ", ".join(missing)
                        + "). Toronto's apartment-standards bylaw requires landlords to keep "
                        "these. Gaps mean problems aren't tracked — and weaken your evidence if "
                        "you ever need to escalate to the Landlord and Tenant Board."
                    ),
                    severity=Severity.HIGH,
                    newcomer_relevant=True,
                    group=Group.ESSENTIAL.value,
                    evidence=f"{len(missing)} record categories scored poor.",
                )
            )

        # Large share of the building not inspectable (obstructed / refused).
        n_obstructed = sum(1 for c in by_key.values() if c.is_not_assessed)
        if n_obstructed >= 10:
            flags.append(
                RedFlag(
                    code="derived:obstructed",
                    title="Much of the building could not be inspected",
                    detail=(
                        f"The City inspector was unable to assess {n_obstructed} areas — typically "
                        "because access was obstructed or refused. That leaves big blind spots in "
                        "what's known about the building's safety and condition, and refused access "
                        "is itself a warning sign about how the building is run."
                    ),
                    severity=Severity.HIGH,
                    newcomer_relevant=True,
                    evidence=f"{n_obstructed} categories recorded as obstructed/refused (score 0).",
                )
            )

        # Stale inspection.
        if ev.evaluation_completed_on:
            age_years = (self.today - ev.evaluation_completed_on).days / 365.25
            if age_years >= 3:
                flags.append(
                    RedFlag(
                        code="derived:stale",
                        title="Inspection data may be out of date",
                        detail=(
                            f"The most recent City evaluation was about {age_years:.0f} years ago. "
                            "Conditions — for better or worse — may have changed since then."
                        ),
                        severity=Severity.MINOR,
                        newcomer_relevant=False,
                        evidence=f"Last evaluated {ev.evaluation_completed_on.isoformat()}.",
                    )
                )

        return flags

    # ------------------------------------------------------------------
    def _group_breakdown(self, cats: list[CategoryScore]) -> list[GroupScore]:
        groups: dict[str, list[CategoryScore]] = {}
        for c in cats:
            groups.setdefault(c.group, []).append(c)

        out: list[GroupScore] = []
        # Preserve a sensible, stable group order.
        order = [g.value for g in Group]
        for gname in order:
            members = groups.get(gname, [])
            if not members:
                continue
            scored = [(c.score, c.weight) for c in members if c.score in (1, 2, 3)]
            subscore: int | None = None
            if scored:
                wsum = sum(w for _, w in scored)
                avg = sum(s * w for s, w in scored) / wsum if wsum else None
                if avg is not None:
                    subscore = _round_or_none((avg - 1) / 2 * 100)
            n_not_assessed = sum(1 for c in members if c.is_not_assessed)
            if subscore is None:
                status = "not assessed" if n_not_assessed else "unknown"
            elif subscore >= 80:
                status = "good"
            elif subscore >= 50:
                status = "adequate"
            else:
                status = "poor"
            out.append(
                GroupScore(
                    group=gname,
                    subscore=subscore,
                    status=status,
                    n_categories=len(members),
                    n_poor=sum(1 for c in members if c.is_poor),
                    n_not_assessed=n_not_assessed,
                )
            )
        return out

    # ------------------------------------------------------------------
    def _strengths(self, cats: list[CategoryScore], building: Building) -> list[Strength]:
        out: list[Strength] = [
            Strength(title=f"{c.label} is well maintained", group=c.group)
            for c in cats
            if c.is_good and c.weight >= 4
        ]
        if building.score_trend is not None and building.score_trend >= 5:
            out.insert(
                0,
                Strength(title=f"Condition is improving (+{building.score_trend} since last evaluation)"),
            )
        return out[:6]

    # ------------------------------------------------------------------
    def _trend(self, building: Building) -> TrendInfo:
        def _year(e):
            return e.year_evaluated or (
                e.evaluation_completed_on.year if e.evaluation_completed_on else None
            )

        timeline = [
            {"year": _year(e), "score": e.score}
            for e in ([building.current] + building.history)
            if e.score is not None and _year(e) is not None
        ]
        # De-duplicate years (keep the latest score for a given year) and sort.
        by_year: dict[int, int] = {}
        for d in timeline:
            by_year[d["year"]] = d["score"]
        timeline = [{"year": y, "score": s} for y, s in sorted(by_year.items())]
        delta = building.score_trend
        if delta is None or len(timeline) < 2:
            return TrendInfo(direction="unknown", history=timeline,
                             narrative="Not enough evaluation history to establish a trend.")
        direction = "improving" if delta >= 5 else "declining" if delta <= -5 else "stable"
        frm, to = timeline[0], timeline[-1]
        narrative = {
            "improving": f"Improving: up {delta} points since the previous evaluation.",
            "declining": f"Declining: down {abs(delta)} points since the previous evaluation — "
            "the building is getting worse, not better.",
            "stable": "Roughly stable across evaluations.",
        }[direction]
        return TrendInfo(
            direction=direction, delta=delta,
            from_year=frm["year"], to_year=to["year"],
            history=timeline, narrative=narrative,
        )

    # ------------------------------------------------------------------
    def _composite_risk(
        self, score: int | None, flags: list[RedFlag], building: Building, trend: TrendInfo
    ) -> int:
        base = (100 - score) if score is not None else 50
        penalty = 0
        penalty += 6 * sum(1 for f in flags if f.severity is Severity.CRITICAL)
        penalty += 3 * sum(1 for f in flags if f.severity is Severity.HIGH)
        penalty += 1 * sum(1 for f in flags if f.severity is Severity.MODERATE)
        if building.current.has_reactive_issues:
            penalty += 6
        if trend.direction == "declining":
            penalty += 8 if (trend.delta or 0) <= -15 else 4
        penalty = min(penalty, 35)  # keep the City score the dominant term
        return max(0, min(100, base + penalty))

    # ------------------------------------------------------------------
    def _newcomer_lens(self, risk_score: int, flags: list[RedFlag]) -> NewcomerLens:
        nc = [f for f in flags if f.newcomer_relevant]
        bump = 5 * sum(1 for f in nc if f.severity in (Severity.CRITICAL, Severity.HIGH))
        nc_score = max(0, min(100, risk_score + min(bump, 20)))
        priorities = sorted(nc, key=lambda f: -f.severity.rank)[:5]

        questions: list[str] = []
        seen: set[str] = set()
        for f in priorities:
            q = QUESTION_BY_KEY.get(f.category_key or "")
            if q and q not in seen:
                questions.append(q)
                seen.add(q)
            elif f.code == "derived:reactive":
                q = "Ask the landlord directly whether there are any open City work orders on the building."
                if q not in seen:
                    questions.append(q)
                    seen.add(q)
        if not questions:
            questions.append(
                "Ask to see the building's most recent City inspection results, and check "
                "RentSafeTO before you sign."
            )

        level = _level_for(nc_score)
        if not nc:
            summary = (
                "Nothing in the City's data stands out as a specific newcomer risk for this "
                "building — but always verify conditions in person before signing."
            )
        else:
            summary = (
                f"For someone new to Toronto, this building carries {level.lower()} risk. The issues "
                "below are the ones easiest to miss and hardest to fix once you've moved in."
            )
        return NewcomerLens(
            risk_score=nc_score, risk_level=level, summary=summary,
            priorities=priorities, questions_to_ask=questions,
        )

    # ------------------------------------------------------------------
    def _headline_factors(self, r: RiskReport) -> list[str]:
        out: list[str] = []
        if r.overall_score is not None:
            out.append(f"City score {r.overall_score}/100 (Grade {r.grade})")
        n_crit = sum(1 for f in r.red_flags if f.severity in (Severity.CRITICAL, Severity.HIGH))
        if n_crit:
            out.append(f"{n_crit} serious deficienc{'y' if n_crit == 1 else 'ies'}")
        top = next((f for f in r.red_flags if f.severity is Severity.CRITICAL), None)
        if top:
            out.append(top.title)
        if r.trend.direction == "declining":
            out.append(f"Condition declining ({r.trend.delta} pts)")
        elif r.trend.direction == "improving":
            out.append(f"Condition improving (+{r.trend.delta} pts)")
        return out[:4]

    # ------------------------------------------------------------------
    def _summary_line(self, r: RiskReport) -> str:
        sev_flags = [f for f in r.red_flags if f.severity in (Severity.CRITICAL, Severity.HIGH)]
        topics = ", ".join(
            f.title.split(":")[0].lower() for f in sev_flags[:3]
        )
        score_part = (
            f"scored {r.overall_score}/100 on its last City inspection"
            if r.overall_score is not None
            else "has no recent City score on file"
        )
        if r.risk_level in ("High", "Severe"):
            lead = f"{r.risk_level} risk: this building {score_part}"
            if topics:
                lead += f", with issues including {topics}"
            if r.trend.direction == "declining":
                lead += ", and its condition is declining"
            return lead + "."
        if r.risk_level == "Elevated":
            lead = f"Elevated risk: this building {score_part}"
            return lead + (f", with concerns around {topics}." if topics else ".")
        if r.risk_level == "Moderate":
            return f"Moderate risk: this building {score_part}, with a few minor concerns to verify in person."
        return f"Low risk: this building {score_part}, with no major deficiencies in the City's data."


# Module-level convenience.
_engine = RiskEngine()


def assess(building: Building) -> RiskReport:
    """Assess a building with a shared default engine."""
    return _engine.assess(building)
