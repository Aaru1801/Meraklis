"""Operator entity resolution (Python port of the team's resolveOperator).

The same real company appears under many raw spellings in the City data — typos,
corporate-suffix variants ("PARK PROPERTY MGMT INC" vs "Park Property Management"),
and the hard case: acronyms that share almost no characters with the full name
("TCH" vs "TORONTO COMMUNITY HOUSING CORPORATION"). Given one building's raw
operator name we want the FULL set of spellings for that company, so the portfolio
query can pull every building it runs.

Cheap-first, model-for-the-hard-part:
  1. Normalize (uppercase, strip punctuation + corporate suffixes, expand
     abbreviations) and cheap-cluster obvious matches (normalized-equal or high
     string similarity) — nails typos + suffix/abbreviation variants for free.
  2. Shortlist names that MIGHT be the same (shared distinctive token, acronym
     relationship, or moderate similarity) and ask the LOCAL model which are truly
     the same company — the only thing that can justify TCH → Toronto Community
     Housing. Its decision + reasoning is the showpiece, grounded and auditable.
  3. If the model is down/unparseable, fall back to the cheap cluster and say so.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from ..data.operators import distinct_operator_raws
from .edge_runtime import LocalModelAdapter, ModelCallSummary

CORPORATE_SUFFIXES = {
    "INC", "INCORPORATED", "LTD", "LTEE", "LIMITED", "LLC", "LLP", "LP", "GP",
    "CORP", "CORPORATION", "CO", "COMPANY", "ULC", "PLC",
}
ABBREVIATIONS = {
    "MGMT": "MANAGEMENT", "MGT": "MANAGEMENT", "MGMNT": "MANAGEMENT", "MNGMT": "MANAGEMENT",
    "PROPERTIES": "PROPERTY", "PROP": "PROPERTY", "PROPS": "PROPERTY",
    "APTS": "APARTMENTS", "APT": "APARTMENTS", "APARTMENT": "APARTMENTS",
    "RESIDENCES": "RESIDENCE", "DEV": "DEVELOPMENTS", "DEVELOPMENT": "DEVELOPMENTS",
    "HLDGS": "HOLDINGS", "INTL": "INTERNATIONAL", "CDN": "CANADIAN",
}
GENERIC_TOKENS = {
    "PROPERTY", "MANAGEMENT", "APARTMENTS", "REALTY", "RENTAL", "RENTALS", "HOLDINGS",
    "HOUSING", "COMMUNITY", "RESIDENTIAL", "RESIDENCE", "GROUP", "DEVELOPMENTS",
    "INVESTMENTS", "INVESTMENT", "REAL", "ESTATE", "SERVICES", "SERVICE", "THE", "AND",
    "OF", "TRUST", "REIT", "CAPITAL", "ASSET", "ASSETS", "PARTNERS", "ENTERPRISES",
    "CANADA", "CANADIAN", "TORONTO", "ONTARIO",
}
SHORTLIST_CAP = 40
CHEAP_MERGE_SIM = 0.9
CANDIDATE_SIM = 0.55


@dataclass(slots=True)
class ResolvedOperator:
    canonical_name: str
    members: list[str]
    confidence: float
    reasoning: str


class _Verdict(BaseModel):
    canonicalName: str = ""
    members: list[str] = []
    confidence: float = 0.5
    reasoning: str = ""


# --- normalization ---------------------------------------------------------
def _tokenize(name: str) -> list[str]:
    raw = name.upper().replace("&", " AND ")
    cleaned = "".join(ch if ch.isalnum() else " " for ch in raw)
    toks = [ABBREVIATIONS.get(t, t) for t in cleaned.split()]
    return [t for t in toks if t and t not in CORPORATE_SUFFIXES]


def _norm_key(name: str) -> str:
    return " ".join(_tokenize(name))


def _acronym(tokens: list[str]) -> str:
    return "".join(t[0] for t in tokens if t)


def _distinctive(tokens: list[str]) -> set[str]:
    return {t for t in tokens if len(t) >= 3 and t not in GENERIC_TOKENS}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        curr = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[len(b)]


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    m = max(len(a), len(b))
    return 1.0 if m == 0 else 1.0 - _levenshtein(a, b) / m


def _is_acronym_of(short: str, long_tokens: list[str]) -> bool:
    if len(long_tokens) < 2 or not (2 <= len(short) <= 6 and short.isalpha()):
        return False
    initials = _acronym(long_tokens)
    if initials == short:
        return True
    return initials.startswith(short) and len(short) >= len(long_tokens) - 1


@dataclass(slots=True)
class _Candidate:
    raw: str
    reason: str


def _build_candidates(target: str, all_names: list[str]) -> tuple[list[str], list[_Candidate]]:
    target_key = _norm_key(target)
    target_tokens = _tokenize(target)
    target_distinct = _distinctive(target_tokens)
    target_is_acronym = 2 <= len(target_key.replace(" ", "")) <= 6 and target_key.replace(" ", "").isalpha()

    cheap = {target}
    shortlist: list[_Candidate] = []
    for raw in all_names:
        if raw == target:
            continue
        key = _norm_key(raw)
        tokens = _tokenize(raw)
        sim = _similarity(target_key, key)
        if key == target_key or sim >= CHEAP_MERGE_SIM:
            cheap.add(raw)
            continue
        reasons: list[str] = []
        if target_is_acronym and _is_acronym_of(target_key.replace(" ", ""), tokens):
            reasons.append(f'"{target}" could be an acronym of this name')
        raw_is_acronym = 2 <= len(key.replace(" ", "")) <= 6 and key.replace(" ", "").isalpha()
        if raw_is_acronym and _is_acronym_of(key.replace(" ", ""), target_tokens):
            reasons.append(f'this name could be an acronym of "{target}"')
        shared = _distinctive(tokens) & target_distinct
        if shared:
            reasons.append(f"shares distinctive token(s): {', '.join(sorted(shared))}")
        if sim >= CANDIDATE_SIM:
            reasons.append(f"string similarity {sim:.2f}")
        if reasons:
            shortlist.append(_Candidate(raw, "; ".join(reasons)))

    def score(c: _Candidate) -> float:
        s = 0.0
        if "acronym" in c.reason:
            s += 100
        if "distinctive token" in c.reason:
            s += 50
        import re

        m = re.search(r"similarity (\d\.\d+)", c.reason)
        if m:
            s += float(m.group(1)) * 10
        return s

    shortlist.sort(key=score, reverse=True)
    return list(cheap), shortlist[:SHORTLIST_CAP]


def _title(name: str) -> str:
    return " ".join(w.capitalize() for w in _norm_key(name).split())


_SYSTEM = (
    "You are an entity-resolution expert for a municipal landlord dataset. You decide "
    "which raw operator-name spellings refer to the SAME real company. Acronyms and "
    "abbreviations count as the same company (e.g. 'TCH' = 'Toronto Community Housing "
    "Corporation'). Be careful: do NOT merge genuinely different companies that merely "
    "share a generic word like 'Property' or 'Management'. Respond with a single JSON object only."
)


def _user_prompt(target: str, cheap: list[str], shortlist: list[_Candidate]) -> str:
    cheap_list = ""
    if len(cheap) > 1:
        cheap_list = "\nAlready-merged spellings (normalization/typo variants — same company):\n" + "\n".join(
            f"  - {m}" for m in cheap
        )
    cand = "\n".join(f"  - {c.raw}    [hint: {c.reason}]" for c in shortlist) or "  (none)"
    return (
        f'TARGET operator name: "{target}"\n'
        f"{cheap_list}\n\n"
        f"CANDIDATE names that MIGHT be the same real company:\n{cand}\n\n"
        'Which candidates are the SAME real company as the TARGET? Include the target and its '
        'already-merged spellings in "members". Use the EXACT raw strings as given. Return JSON:\n'
        "{\n"
        '  "canonicalName": string,   // FULL human-readable company name; expand acronyms (e.g. "Toronto Community Housing Corporation", never "TCH")\n'
        '  "members": string[],\n'
        '  "confidence": number,\n'
        '  "reasoning": string\n'
        "}"
    )


async def resolve_operator(
    target_raw: str, model: LocalModelAdapter
) -> tuple[ResolvedOperator, ModelCallSummary | None]:
    """Resolve a raw operator spelling to its full company + member spellings."""
    target = target_raw.strip()
    all_names = distinct_operator_raws()
    valid = set(all_names)
    cheap, shortlist = _build_candidates(target, all_names)
    fallback_canonical = _title(target)

    # Nothing for the model to weigh in on — cheap clustering already has it.
    if not shortlist:
        return (
            ResolvedOperator(
                canonical_name=fallback_canonical,
                members=cheap,
                confidence=0.85 if len(cheap) > 1 else 0.7,
                reasoning=(
                    f"Matched {len(cheap)} spelling(s) by normalization (suffix/abbreviation/typo "
                    "variants); no other plausible candidates to resolve."
                    if len(cheap) > 1
                    else "Single distinct spelling; no other candidate shares a distinctive token or acronym."
                ),
            ),
            None,
        )

    verdict, call = await model.generate_json(
        agent="Operator / Portfolio Agent",
        response_model=_Verdict,
        temperature=0.1,
        # Reasoning models (Nemotron) spend tokens "thinking" before the answer;
        # the entity-resolution prompt is dense, so give it ample room to finish
        # its chain-of-thought AND still emit the JSON verdict in `content`.
        max_tokens=2048,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _user_prompt(target, cheap, shortlist)},
        ],
    )

    if verdict is None:
        # Model unavailable / unparseable — honest cheap-cluster fallback.
        return (
            ResolvedOperator(
                canonical_name=fallback_canonical,
                members=cheap,
                confidence=0.6 if len(cheap) > 1 else 0.4,
                reasoning=(
                    "Model resolution unavailable; fell back to normalization clustering only. "
                    "Acronym/abbreviation links were NOT evaluated."
                ),
            ),
            call,
        )

    members = set(cheap)
    for m in verdict.members or []:
        if m in valid:
            members.add(m)
    members.add(target)
    confidence = max(0.0, min(1.0, verdict.confidence)) if isinstance(verdict.confidence, (int, float)) else 0.5

    return (
        ResolvedOperator(
            canonical_name=(verdict.canonicalName.strip() or fallback_canonical),
            members=list(members),
            confidence=confidence,
            reasoning=verdict.reasoning.strip() or "(model returned no reasoning)",
        ),
        call,
    )
