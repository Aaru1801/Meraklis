"""Multi-source data adapter layer.

Every external housing source (municipal open data, listing portals) is wrapped
in a :class:`SourceAdapter` that returns a uniform :class:`AdapterResult` with an
explicit *status* and *confidence*. This is what lets the Research agent treat
heterogeneous, sometimes-missing data honestly: a source that is down, or whose
data is ambiguous, is reported as such — never silently dropped and never
hallucinated into a false certainty.
"""

from __future__ import annotations

import datetime as dt
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from ..address import normalize_address


class SourceStatus(str, Enum):
    OK = "ok"  # data retrieved with confidence
    UNCERTAIN = "uncertain"  # retrieved, but ambiguous / partial / stale
    UNAVAILABLE = "unavailable"  # source has no data for this query / not wired
    ERROR = "error"  # source errored or timed out (graceful degradation)


@dataclass(slots=True)
class AddressQuery:
    """A normalized query passed to every adapter."""

    raw_address: str = ""
    rsn: str | None = None
    canonical_address: str = ""

    @classmethod
    def make(cls, raw_address: str = "", rsn: str | None = None) -> "AddressQuery":
        return cls(
            raw_address=raw_address,
            rsn=rsn,
            canonical_address=normalize_address(raw_address).canonical if raw_address else "",
        )


@dataclass(slots=True)
class AdapterResult:
    """Uniform result from any source adapter."""

    source: str
    status: SourceStatus
    confidence: float  # 0.0–1.0
    data: dict = field(default_factory=dict)
    note: str = ""
    fetched_at: str = field(default_factory=lambda: dt.datetime.now(dt.UTC).isoformat())

    @property
    def usable(self) -> bool:
        return self.status in (SourceStatus.OK, SourceStatus.UNCERTAIN) and bool(self.data)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "status": self.status.value,
            "confidence": round(self.confidence, 2),
            "note": self.note,
            "fetched_at": self.fetched_at,
            "has_data": bool(self.data),
        }


class SourceAdapter(ABC):
    """Base class for a data source. Implementations must be fault-tolerant."""

    name: str = "source"
    #: Default trust we place in this source when it returns data.
    base_confidence: float = 0.8

    def available(self) -> bool:
        """Whether this source is wired up and reachable. Default: True."""
        return True

    @abstractmethod
    def _fetch(self, query: AddressQuery) -> AdapterResult:
        """Source-specific fetch. May raise — :meth:`fetch` guards it."""

    def fetch(self, query: AddressQuery) -> AdapterResult:
        """Fetch with graceful degradation — never raises."""
        if not self.available():
            return AdapterResult(
                source=self.name,
                status=SourceStatus.UNAVAILABLE,
                confidence=0.0,
                note=f"{self.name} is not configured/available.",
            )
        try:
            return self._fetch(query)
        except Exception as exc:  # noqa: BLE001 - fault tolerance is the point
            return AdapterResult(
                source=self.name,
                status=SourceStatus.ERROR,
                confidence=0.0,
                note=f"{self.name} fetch failed: {type(exc).__name__}: {exc}",
            )
