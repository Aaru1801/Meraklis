"""Multi-source data adapter layer."""

from .base import AddressQuery, AdapterResult, SourceAdapter, SourceStatus
from .market import HouseSigmaAdapter, RealtorCaAdapter
from .massing import MassingAdapter
from .rentsafeto_adapter import RentSafeToAdapter

__all__ = [
    "AddressQuery",
    "AdapterResult",
    "SourceAdapter",
    "SourceStatus",
    "RentSafeToAdapter",
    "RealtorCaAdapter",
    "HouseSigmaAdapter",
    "MassingAdapter",
]
