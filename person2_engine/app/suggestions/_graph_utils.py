"""
_graph_utils.py — small, dependency-free union-find + Kruskal's MST used by
redundancy.py to cluster highly-correlated numeric columns. Kept dependency-free
(no networkx/scipy.sparse.csgraph) since it's ~20 lines of real graph algorithm
and this keeps the suggestions package free of extra install surface.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

Edge = Tuple[str, str, float]  # (col_a, col_b, correlation)


class _UnionFind:
    def __init__(self, items: Sequence[str]):
        self._parent = {x: x for x in items}
        self._rank = {x: 0 for x in items}

    def find(self, x: str) -> str:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1
        return True


def build_mst_edges(columns: List[str], corr_matrix: Dict[str, Dict[str, float]]) -> List[Edge]:
    """Kruskal's MST over the complete graph of `columns`, using
    weight = 1 - |correlation| (so highly-correlated pairs are "cheap" edges
    and get pulled into the tree first). Returns the MST edges as
    (col_a, col_b, correlation) — weight is recomputable from correlation.
    """
    candidate_edges = []
    for i, a in enumerate(columns):
        for b in columns[i + 1 :]:
            corr = corr_matrix.get(a, {}).get(b)
            if corr is None:
                corr = corr_matrix.get(b, {}).get(a)
            if corr is None:
                continue
            weight = 1.0 - abs(corr)
            candidate_edges.append((weight, a, b, corr))

    candidate_edges.sort(key=lambda e: e[0])
    uf = _UnionFind(columns)
    mst_edges: List[Edge] = []
    for _weight, a, b, corr in candidate_edges:
        if uf.union(a, b):
            mst_edges.append((a, b, corr))
    return mst_edges


def connected_components(nodes: Sequence[str], edges: List[Edge]) -> List[List[str]]:
    """Connected components induced by `edges` only (nodes with no edge are
    left out entirely — callers only care about clusters of size >= 2)."""
    involved = set()
    for a, b, _ in edges:
        involved.add(a)
        involved.add(b)

    uf = _UnionFind(list(involved))
    for a, b, _ in edges:
        uf.union(a, b)

    groups: Dict[str, List[str]] = {}
    for node in involved:
        groups.setdefault(uf.find(node), []).append(node)
    return list(groups.values())
