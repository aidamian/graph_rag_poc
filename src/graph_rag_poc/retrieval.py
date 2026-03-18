from __future__ import annotations

import math
import re
from collections import defaultdict
from itertools import combinations

import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from graph_rag_poc.logging_utils import get_logger
from graph_rag_poc.models import GraphEdge, GraphNode, PathInsight, RetrievalCandidate, RetrievalOutcome


TOKEN_RE = re.compile(r"[a-z0-9_.-]+")
EXACT_ENTITY_RE = re.compile(r"(cve-\d{4}-\d+|t\d{4}(?:\.\d{3})?)", re.IGNORECASE)

RELATION_BONUS = {
    "EXPLOITS": 0.28,
    "INDICATES": 0.22,
    "PRECEDES": 0.20,
    "MITIGATES": 0.18,
    "CONNECTS_TO": 0.16,
    "EVIDENCED_BY": 0.14,
    "AFFECTS": 0.12,
    "USES": 0.12,
    "OBSERVED_ON": 0.10,
    "RECOMMENDS": 0.08,
}

ACTION_HINTS = {"contain", "mitigate", "next", "recommend", "do", "response", "hours"}
CHAIN_HINTS = {"connect", "connected", "link", "chain", "path", "how", "why"}


def normalize(text: str) -> str:
    return " ".join(TOKEN_RE.findall(text.lower()))


def tokenize(text: str) -> set[str]:
    return set(TOKEN_RE.findall(text.lower()))


class KnowledgeGraphIndex:
    def __init__(self, nodes: tuple[GraphNode, ...], edges: tuple[GraphEdge, ...]) -> None:
        self.logger = get_logger("RETRIEVE")
        self.nodes = {node.id: node for node in nodes}
        self.edges = list(edges)
        self.node_ids = list(self.nodes)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        corpus = [self.nodes[node_id].retrieval_text for node_id in self.node_ids]
        self.matrix = self.vectorizer.fit_transform(corpus)
        self.alias_index = self._build_alias_index()

        self.graph = nx.Graph()
        for node in nodes:
            self.graph.add_node(node.id)
        for edge in edges:
            self.graph.add_edge(
                edge.source,
                edge.target,
                type=edge.type,
                description=edge.description,
                weight=edge.weight,
            )

    def retrieve(self, question: str, mode: str = "graph", top_k: int = 8) -> RetrievalOutcome:
        if mode == "vector":
            return self._vector_only(question, top_k=top_k)
        return self._graph_rag(question, top_k=top_k)

    def subgraph(self, outcome: RetrievalOutcome) -> tuple[tuple[GraphNode, ...], tuple[GraphEdge, ...]]:
        selected_ids: set[str] = {candidate.node_id for candidate in outcome.candidates}
        for path in outcome.paths:
            selected_ids.update(path.node_ids)

        sub_nodes = tuple(
            self.nodes[node_id]
            for node_id in self.node_ids
            if node_id in selected_ids
        )
        sub_edges = tuple(
            edge
            for edge in self.edges
            if edge.source in selected_ids and edge.target in selected_ids
        )
        return sub_nodes, sub_edges

    def related_controls(self, node_ids: set[str], limit: int = 4) -> list[GraphNode]:
        scored: dict[str, float] = defaultdict(float)
        for node_id in node_ids:
            if node_id not in self.graph:
                continue
            for neighbor in self.graph.neighbors(node_id):
                node = self.nodes[neighbor]
                if node.kind != "Control":
                    continue
                edge = self.graph[node_id][neighbor]
                scored[neighbor] += 1.0 + edge.get("weight", 1.0)
        ordered = sorted(scored.items(), key=lambda item: (-item[1], self.nodes[item[0]].name))
        return [self.nodes[node_id] for node_id, _ in ordered[:limit]]

    def _vector_only(self, question: str, top_k: int) -> RetrievalOutcome:
        base_scores, reasons, query_entities = self._base_scores(question)
        ranked_ids = sorted(base_scores, key=lambda node_id: (-base_scores[node_id], self.nodes[node_id].name))
        candidates = tuple(
            RetrievalCandidate(
                node_id=node_id,
                score=round(base_scores[node_id], 4),
                reasons=tuple(reasons[node_id]) or ("semantic similarity",),
                hop_distance=0,
                seed=index < min(4, top_k),
            )
            for index, node_id in enumerate(ranked_ids[:top_k])
        )
        self.logger.info(
            "vector_retrieval_complete",
            query=question,
            top_ids=[candidate.node_id for candidate in candidates],
        )
        return RetrievalOutcome(
            mode="vector",
            question=question,
            query_entity_ids=tuple(query_entities),
            candidates=candidates,
            paths=(),
            explanation="Vector-only retrieval ranks directly similar graph entities but does not expand through the investigation graph.",
            cypher_preview="MATCH (n:Entity) WHERE n.id IN $top_ids RETURN n",
            metrics={
                "candidate_count": len(candidates),
                "query_entity_count": len(query_entities),
                "mode": "vector",
            },
        )

    def _graph_rag(self, question: str, top_k: int) -> RetrievalOutcome:
        base_scores, reasons, query_entities = self._base_scores(question)
        seed_ids = sorted(base_scores, key=lambda node_id: (-base_scores[node_id], self.nodes[node_id].name))[:4]
        action_request = self._is_action_request(question)
        chain_request = self._is_chain_request(question)

        graph_bonus: dict[str, float] = defaultdict(float)
        graph_reasons: dict[str, list[str]] = defaultdict(list)

        for seed_id in seed_ids:
            seed_score = base_scores[seed_id] + 0.25
            graph_bonus[seed_id] += seed_score
            graph_reasons[seed_id].append("seed entity for graph expansion")

            for path in nx.single_source_shortest_path(self.graph, seed_id, cutoff=2).values():
                hop_distance = len(path) - 1
                if hop_distance <= 0:
                    continue
                current = path[-1]
                edge_bonus = self._path_bonus(path, question)
                decay = 0.60 if hop_distance == 1 else 0.35
                bonus = seed_score * decay + edge_bonus + self._kind_bonus(self.nodes[current].kind, action_request, chain_request)
                graph_bonus[current] += bonus
                graph_reasons[current].append(
                    f"{hop_distance}-hop graph expansion from {self.nodes[seed_id].name}"
                )

        combined_scores = {
            node_id: round(base_scores[node_id] * 0.60 + graph_bonus[node_id], 4)
            for node_id in self.node_ids
        }
        ranked_ids = sorted(
            combined_scores,
            key=lambda node_id: (-combined_scores[node_id], self.nodes[node_id].name),
        )

        paths = self._extract_paths(seed_ids, ranked_ids[: max(top_k, 6)], combined_scores)
        selected_ids: set[str] = set(ranked_ids[:top_k])
        for path in paths:
            selected_ids.update(path.node_ids)

        if chain_request:
            selected_ids.update(self._top_kind_ids(combined_scores, "Technique", limit=4))
            for node_id in list(selected_ids):
                if node_id not in self.graph:
                    continue
                for neighbor in self.graph.neighbors(node_id):
                    if self.nodes[neighbor].kind == "Technique":
                        selected_ids.add(neighbor)

        if action_request:
            selected_ids.update(self._top_kind_ids(combined_scores, "Control", limit=4))
            for control in self.related_controls(selected_ids, limit=4):
                selected_ids.add(control.id)

        ordered_selected = sorted(
            selected_ids,
            key=lambda node_id: (-combined_scores.get(node_id, 0.0), self.nodes[node_id].name),
        )

        candidates = []
        for node_id in ordered_selected:
            node_reasons = reasons[node_id] + graph_reasons[node_id]
            hop_distance = self._hop_distance(seed_ids, node_id)
            candidates.append(
                RetrievalCandidate(
                    node_id=node_id,
                    score=round(combined_scores[node_id], 4),
                    reasons=tuple(node_reasons) or ("graph expansion",),
                    hop_distance=hop_distance,
                    seed=node_id in seed_ids,
                )
            )

        self.logger.info(
            "graph_retrieval_complete",
            query=question,
            seed_ids=seed_ids,
            selected_ids=[candidate.node_id for candidate in candidates[:top_k]],
            path_count=len(paths),
        )

        return RetrievalOutcome(
            mode="graph",
            question=question,
            query_entity_ids=tuple(query_entities),
            candidates=tuple(candidates),
            paths=paths,
            explanation="Graph-aware retrieval starts from direct matches, expands through related alerts, assets, techniques, and controls, then keeps the connected investigation path.",
            cypher_preview=(
                "MATCH p = (seed:Entity)-[:RELATES_TO*1..2]-(neighbor:Entity) "
                "WHERE seed.id IN $seed_ids RETURN p LIMIT 25"
            ),
            metrics={
                "candidate_count": len(candidates),
                "query_entity_count": len(query_entities),
                "seed_count": len(seed_ids),
                "path_count": len(paths),
                "mode": "graph",
            },
        )

    def _base_scores(self, question: str) -> tuple[dict[str, float], dict[str, list[str]], list[str]]:
        query_norm = normalize(question)
        query_tokens = tokenize(question)
        direct_entities = self._extract_query_entities(question)
        query_vector = self.vectorizer.transform([query_norm])
        similarities = cosine_similarity(query_vector, self.matrix)[0]

        scores: dict[str, float] = {}
        reasons: dict[str, list[str]] = defaultdict(list)

        for index, node_id in enumerate(self.node_ids):
            node = self.nodes[node_id]
            score = float(similarities[index])

            overlap = len(query_tokens.intersection(tokenize(node.name)))
            if overlap:
                score += min(0.18, overlap * 0.06)
                reasons[node_id].append("keyword overlap with node name")

            if node_id in direct_entities:
                score += 0.60
                reasons[node_id].append("explicit entity match in the question")

            if node.kind == "Control" and self._is_action_request(question):
                score += 0.06
                reasons[node_id].append("control bias for action-oriented question")

            scores[node_id] = round(score, 4)

        return scores, reasons, direct_entities

    def _extract_query_entities(self, question: str) -> list[str]:
        question_norm = f" {normalize(question)} "
        matches: set[str] = set()

        for match in EXACT_ENTITY_RE.findall(question):
            normalized = normalize(match)
            matches.update(self.alias_index.get(normalized, set()))

        for alias, node_ids in self.alias_index.items():
            if len(alias) < 4:
                continue
            if f" {alias} " in question_norm:
                matches.update(node_ids)

        return sorted(matches)

    def _build_alias_index(self) -> dict[str, set[str]]:
        index: dict[str, set[str]] = defaultdict(set)
        for node in self.nodes.values():
            phrases = {node.name, node.id, *node.aliases}
            for phrase in phrases:
                index[normalize(phrase)].add(node.id)
        return index

    def _extract_paths(
        self,
        seed_ids: list[str],
        ranked_ids: list[str],
        combined_scores: dict[str, float],
    ) -> tuple[PathInsight, ...]:
        candidates: list[tuple[float, PathInsight]] = []
        seen: set[tuple[str, ...]] = set()

        for left_id, right_id in combinations(seed_ids + ranked_ids[:4], 2):
            if left_id == right_id:
                continue
            try:
                path = nx.shortest_path(self.graph, left_id, right_id)
            except nx.NetworkXNoPath:
                continue
            if len(path) < 3 or len(path) > 6:
                continue
            path_key = tuple(path)
            reverse_key = tuple(reversed(path))
            if path_key in seen or reverse_key in seen:
                continue
            seen.add(path_key)

            edge_types = []
            for source, target in zip(path, path[1:]):
                edge_types.append(self.graph[source][target]["type"])
            score = sum(combined_scores[node_id] for node_id in path) / len(path)
            candidates.append(
                (
                    score,
                    PathInsight(
                        node_ids=tuple(path),
                        edge_types=tuple(edge_types),
                        narrative=self._path_narrative(path, edge_types),
                    ),
                )
            )

        ordered = sorted(candidates, key=lambda item: (-item[0], item[1].narrative))
        return tuple(path for _, path in ordered[:4])

    def _path_narrative(self, path: list[str], edge_types: list[str]) -> str:
        pieces = [self.nodes[path[0]].name]
        for edge_type, node_id in zip(edge_types, path[1:]):
            pieces.append(f"{edge_type.lower().replace('_', ' ')} {self.nodes[node_id].name}")
        return " -> ".join(pieces)

    def _path_bonus(self, path: list[str], question: str) -> float:
        bonus = 0.0
        for source, target in zip(path, path[1:]):
            bonus += RELATION_BONUS.get(self.graph[source][target]["type"], 0.05)
        if self._is_chain_request(question):
            bonus += 0.10
        return bonus

    def _kind_bonus(self, kind: str, action_request: bool, chain_request: bool) -> float:
        if action_request and kind == "Control":
            return 0.24
        if chain_request and kind in {"Technique", "Alert", "Asset", "Incident"}:
            return 0.12
        if kind in {"Incident", "Campaign"}:
            return 0.08
        return 0.0

    def _hop_distance(self, seed_ids: list[str], node_id: str) -> int:
        if node_id in seed_ids:
            return 0
        distances = []
        for seed_id in seed_ids:
            try:
                distances.append(nx.shortest_path_length(self.graph, seed_id, node_id))
            except nx.NetworkXNoPath:
                continue
        return min(distances) if distances else math.inf

    def _top_kind_ids(self, scores: dict[str, float], kind: str, limit: int) -> set[str]:
        ranked = [
            node_id
            for node_id in sorted(scores, key=lambda item: (-scores[item], self.nodes[item].name))
            if self.nodes[node_id].kind == kind
        ]
        return set(ranked[:limit])

    @staticmethod
    def _is_action_request(question: str) -> bool:
        return bool(ACTION_HINTS.intersection(tokenize(question)))

    @staticmethod
    def _is_chain_request(question: str) -> bool:
        return bool(CHAIN_HINTS.intersection(tokenize(question)))
