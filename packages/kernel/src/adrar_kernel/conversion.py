"""
Unit conversion graph resolver.

Invariant §0.9: unit conversion is DATA not code.
All coefficients come from the conversion_factors table passed in.
No hardcoded conversion values here.

The graph is a set of directed edges (from_unit, to_unit, coefficient).
resolve_conversion does BFS to find a path and returns the full chain
with every intermediate step captured (for computation_trace).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from .types import ConversionChain, ConversionEdge, ConversionStep


class ConversionError(Exception):
    pass


def _active_edges(
    edges: Sequence[ConversionEdge],
    on_date: date,
) -> list[ConversionEdge]:
    """Filter edges to those effective on on_date."""
    return [
        e for e in edges
        if e.effective_from <= on_date
        and (e.effective_to is None or e.effective_to >= on_date)
    ]


def _edge_priority(edge: ConversionEdge, fuel_type: str | None) -> int:
    """Lower is better. Fuel-specific edges beat generic ones."""
    if edge.fuel_type is not None and edge.fuel_type == fuel_type:
        return 0   # exact fuel match
    if edge.fuel_type is None:
        return 1   # generic
    return 2       # wrong fuel — should not normally be selected


def resolve_conversion(
    edges: Sequence[ConversionEdge],
    from_unit: str,
    to_unit: str,
    fuel_type: str | None,
    on_date: date,
) -> ConversionChain:
    """
    BFS over the conversion graph to find a path from_unit → to_unit.

    Returns a ConversionChain with every step and the combined coefficient
    (product of all step coefficients).

    Raises ConversionError if no path exists.
    """
    if from_unit == to_unit:
        return ConversionChain(steps=(), combined_coefficient=Decimal("1"))

    active = _active_edges(edges, on_date)

    # Build adjacency: from_unit → list of edges, sorted by priority
    adj: dict[str, list[ConversionEdge]] = {}
    for e in active:
        if e.fuel_type is None or e.fuel_type == fuel_type:
            adj.setdefault(e.from_unit, []).append(e)

    # Sort each adjacency list by priority (fuel-specific first)
    for unit in adj:
        adj[unit].sort(key=lambda e: _edge_priority(e, fuel_type))

    # BFS: state = (current_unit, path_of_edges)
    queue: deque[tuple[str, tuple[ConversionEdge, ...]]] = deque()
    queue.append((from_unit, ()))
    visited: set[str] = {from_unit}

    while queue:
        current_unit, path = queue.popleft()

        for edge in adj.get(current_unit, []):
            next_unit = edge.to_unit
            if next_unit in visited:
                continue
            new_path = path + (edge,)
            if next_unit == to_unit:
                return _build_chain(new_path)
            visited.add(next_unit)
            queue.append((next_unit, new_path))

    raise ConversionError(
        f"No conversion path from '{from_unit}' to '{to_unit}' "
        f"for fuel_type={fuel_type!r} on {on_date}"
    )


def _build_chain(edges: tuple[ConversionEdge, ...]) -> ConversionChain:
    steps = tuple(
        ConversionStep(
            edge_id=e.id,
            from_unit=e.from_unit,
            to_unit=e.to_unit,
            coefficient=e.coefficient,
            conversion_type=e.conversion_type,
            fuel_type=e.fuel_type,
            source=e.source,
        )
        for e in edges
    )
    combined = Decimal("1")
    for e in edges:
        combined *= e.coefficient
    return ConversionChain(steps=steps, combined_coefficient=combined)
