"""Criminal network graph.

Builds a small graph centered on a case OR a suspect, expanding `depth` hops
through `Case.suspect_names`. Two node types (case, suspect) and two edge
types (mentions, co_suspect).

Officer-only — no role-aware filtering happens here; the route enforces that.
Within the graph itself, we surface suspect names verbatim because this
endpoint is gated behind `require_officer`. The audit log captures who looked
at whom.

For the 1100-case corpus we scan in-process. When that stops being fast
enough, this is the function to move into Catalyst Datastore ZCQL or a
proper graph store.
"""

from __future__ import annotations

from collections import defaultdict

from models import Case, EdgeKind, NetworkEdge, NetworkNode, NetworkResponse, NodeKind
from services.datastore import case_repo


# --- index helpers --------------------------------------------------------

def _normalize_name(name: str) -> str | None:
    n = name.strip()
    if not n or n.lower() in ("unknown", "redacted"):
        return None
    return n


def _suspect_node_id(name: str) -> str:
    # Stable + namespaced so node IDs can't collide with case IDs.
    return f"suspect::{name.lower()}"


def _case_node_id(case_id: str) -> str:
    return f"case::{case_id}"


def _build_indices(cases: list[Case]):
    """suspects → list[Case], cases-by-id."""
    by_suspect: dict[str, list[Case]] = defaultdict(list)
    by_case: dict[str, Case] = {}
    for c in cases:
        by_case[c.case_id] = c
        for raw in c.suspect_names:
            name = _normalize_name(raw)
            if name is None:
                continue
            by_suspect[name].append(c)
    return by_suspect, by_case


# --- public API -----------------------------------------------------------

def graph_for_case(case_id: str, depth: int = 1) -> NetworkResponse | None:
    cases = list(case_repo().list(limit=100_000))
    by_suspect, by_case = _build_indices(cases)
    if case_id not in by_case:
        return None

    nodes: dict[str, NetworkNode] = {}
    edges: list[NetworkEdge] = []
    visited_cases: set[str] = set()
    visited_suspects: set[str] = set()

    frontier_cases = {case_id}
    for hop in range(depth + 1):
        next_suspects: set[str] = set()
        for cid in frontier_cases:
            if cid in visited_cases:
                continue
            visited_cases.add(cid)
            case = by_case.get(cid)
            if case is None:
                continue
            nodes[_case_node_id(cid)] = _case_to_node(case)
            for raw in case.suspect_names:
                name = _normalize_name(raw)
                if name is None:
                    continue
                if name not in visited_suspects:
                    next_suspects.add(name)
                nodes[_suspect_node_id(name)] = NetworkNode(
                    id=_suspect_node_id(name),
                    label=name,
                    kind=NodeKind.SUSPECT,
                    properties={"case_count": len(by_suspect.get(name, []))},
                )
                edges.append(NetworkEdge(
                    id=f"edge::{cid}->{name}",
                    source=_case_node_id(cid),
                    target=_suspect_node_id(name),
                    kind=EdgeKind.MENTIONS,
                ))

        # Expand suspects into their other cases for the next hop.
        if hop < depth:
            next_cases: set[str] = set()
            for name in next_suspects:
                visited_suspects.add(name)
                for related in by_suspect.get(name, []):
                    if related.case_id not in visited_cases:
                        next_cases.add(related.case_id)
            frontier_cases = next_cases
        else:
            visited_suspects.update(next_suspects)
            frontier_cases = set()

    edges.extend(_co_suspect_edges(visited_cases, by_case))

    return NetworkResponse(
        center_id=_case_node_id(case_id),
        nodes=list(nodes.values()),
        edges=_dedupe_edges(edges),
        depth=depth,
    )


def graph_for_suspect(name: str, depth: int = 1) -> NetworkResponse | None:
    cases = list(case_repo().list(limit=100_000))
    by_suspect, by_case = _build_indices(cases)
    needle = _normalize_name(name)
    if needle is None or needle.lower() not in {k.lower() for k in by_suspect.keys()}:
        return None
    # Case-fold to the canonical key the index used.
    canonical = next(k for k in by_suspect.keys() if k.lower() == needle.lower())

    nodes: dict[str, NetworkNode] = {
        _suspect_node_id(canonical): NetworkNode(
            id=_suspect_node_id(canonical),
            label=canonical,
            kind=NodeKind.SUSPECT,
            properties={"case_count": len(by_suspect[canonical])},
        )
    }
    edges: list[NetworkEdge] = []
    visited_suspects: set[str] = {canonical}
    visited_cases: set[str] = set()

    frontier_suspects = {canonical}
    for hop in range(depth + 1):
        next_cases: set[str] = set()
        for sname in frontier_suspects:
            for case in by_suspect.get(sname, []):
                if case.case_id in visited_cases:
                    continue
                visited_cases.add(case.case_id)
                next_cases.add(case.case_id)
                nodes[_case_node_id(case.case_id)] = _case_to_node(case)
                edges.append(NetworkEdge(
                    id=f"edge::{case.case_id}->{sname}",
                    source=_case_node_id(case.case_id),
                    target=_suspect_node_id(sname),
                    kind=EdgeKind.MENTIONS,
                ))

        if hop < depth:
            next_suspects: set[str] = set()
            for cid in next_cases:
                case = by_case.get(cid)
                if case is None:
                    continue
                for raw in case.suspect_names:
                    other = _normalize_name(raw)
                    if other is None or other in visited_suspects:
                        continue
                    visited_suspects.add(other)
                    next_suspects.add(other)
                    nodes[_suspect_node_id(other)] = NetworkNode(
                        id=_suspect_node_id(other),
                        label=other,
                        kind=NodeKind.SUSPECT,
                        properties={"case_count": len(by_suspect.get(other, []))},
                    )
                    edges.append(NetworkEdge(
                        id=f"edge::{cid}->{other}",
                        source=_case_node_id(cid),
                        target=_suspect_node_id(other),
                        kind=EdgeKind.MENTIONS,
                    ))
            frontier_suspects = next_suspects
        else:
            frontier_suspects = set()

    edges.extend(_co_suspect_edges(visited_cases, by_case))

    return NetworkResponse(
        center_id=_suspect_node_id(canonical),
        nodes=list(nodes.values()),
        edges=_dedupe_edges(edges),
        depth=depth,
    )


# --- internals ------------------------------------------------------------

def _case_to_node(case: Case) -> NetworkNode:
    return NetworkNode(
        id=_case_node_id(case.case_id),
        label=case.case_id,
        kind=NodeKind.CASE,
        properties={
            "crime_type": case.crime_type,
            "locality": case.locality,
            "status": case.status.value,
            "occurred_on": case.occurred_on.isoformat(),
        },
    )


def _co_suspect_edges(case_ids: set[str], by_case: dict[str, Case]) -> list[NetworkEdge]:
    """For every visited case, connect each pair of suspects with a CO_SUSPECT
    edge. We tally and merge duplicates afterwards."""
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    for cid in case_ids:
        case = by_case.get(cid)
        if case is None:
            continue
        names = sorted({_normalize_name(n) for n in case.suspect_names} - {None})  # type: ignore[arg-type]
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pair_counts[(names[i], names[j])] += 1
    return [
        NetworkEdge(
            id=f"co::{a}::{b}",
            source=_suspect_node_id(a),
            target=_suspect_node_id(b),
            kind=EdgeKind.CO_SUSPECT,
            weight=count,
        )
        for (a, b), count in pair_counts.items()
    ]


def _dedupe_edges(edges: list[NetworkEdge]) -> list[NetworkEdge]:
    seen: dict[str, NetworkEdge] = {}
    for e in edges:
        # CO_SUSPECT pair keys are already normalized by sorting; MENTIONS edges
        # are keyed on case->suspect strings.
        seen[e.id] = e
    return list(seen.values())
