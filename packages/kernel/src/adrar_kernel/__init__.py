# adrar_kernel — pure deterministic emissions calculation kernel
# No network, no LLM, no I/O. Importable by API and tests.
__version__ = "0.1.0"

from .calc import compute_emissions, compute_state_hash
from .conversion import ConversionError, resolve_conversion
from .factors import FactorError, find_factors_for_fact, select_factor_set
from .types import (
    ActivityFact,
    ConversionChain,
    ConversionEdge,
    ConversionStep,
    EmissionFactor,
    EmissionResult,
    FactorSet,
    GWPValue,
    ScopeUncertainty,
    TraceLineItem,
    UncertaintyRange,
)

__all__ = [
    "compute_emissions",
    "compute_state_hash",
    "resolve_conversion",
    "ConversionError",
    "select_factor_set",
    "find_factors_for_fact",
    "FactorError",
    "ActivityFact",
    "ConversionChain",
    "ConversionEdge",
    "ConversionStep",
    "EmissionFactor",
    "EmissionResult",
    "FactorSet",
    "GWPValue",
    "ScopeUncertainty",
    "TraceLineItem",
    "UncertaintyRange",
]
