from __future__ import annotations

from collections import Counter

from graph_rag_poc.answering import DeterministicAnswerGenerator, OpenAIAnswerGenerator
from graph_rag_poc.api_models import (
    AnswerView,
    EdgeView,
    EvidenceView,
    HealthView,
    InvestigationModeView,
    InvestigationResponse,
    NodeView,
    PathView,
    RetrievalView,
    SeedView,
    SummaryView,
    UseCaseView,
)
from graph_rag_poc.config import Settings
from graph_rag_poc.graph_store import Neo4jGraphStore
from graph_rag_poc.logging_utils import get_logger
from graph_rag_poc.models import AnswerOutcome, GraphEdge, GraphNode, RetrievalOutcome, UseCase
from graph_rag_poc.retrieval import KnowledgeGraphIndex
from graph_rag_poc.seed_data import get_demo_use_case


class GraphRagService:
    def __init__(self, settings: Settings, store: Neo4jGraphStore | None = None) -> None:
        self.settings = settings
        self.store = store
        self.logger = get_logger("INGEST")
        self.base_use_case = get_demo_use_case()
        self.use_case: UseCase = self.base_use_case
        self.index = KnowledgeGraphIndex(self.use_case.nodes, self.use_case.edges)

        deterministic = DeterministicAnswerGenerator()
        if settings.openai_enabled and settings.openai_api_key:
            self.answer_generator = OpenAIAnswerGenerator(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
                fallback=deterministic,
            )
        else:
            self.answer_generator = deterministic

    def initialize(self) -> None:
        if not self.store:
            return
        self.store.wait_until_ready()
        self.store.ensure_schema()
        if self.settings.auto_seed and self.store.is_empty():
            self.logger.info("auto_seeding_demo_graph", use_case=self.base_use_case.id)
            self.store.seed(self.base_use_case, reset=True)
        self.refresh_from_store()

    def close(self) -> None:
        if self.store:
            self.store.close()

    def refresh_from_store(self) -> None:
        if not self.store:
            self.index = KnowledgeGraphIndex(self.use_case.nodes, self.use_case.edges)
            return
        nodes, edges = self.store.load_snapshot()
        self.use_case = self.base_use_case.with_snapshot(nodes=nodes, edges=edges)
        self.index = KnowledgeGraphIndex(self.use_case.nodes, self.use_case.edges)
        self.logger.info(
            "graph_index_refreshed",
            nodes=len(self.use_case.nodes),
            edges=len(self.use_case.edges),
        )

    def seed_demo_graph(self, reset: bool = True) -> SeedView:
        if self.store:
            self.store.seed(self.base_use_case, reset=reset)
            self.refresh_from_store()
        else:
            self.use_case = self.base_use_case
            self.index = KnowledgeGraphIndex(self.use_case.nodes, self.use_case.edges)
        return SeedView(
            status="seeded",
            node_count=len(self.use_case.nodes),
            edge_count=len(self.use_case.edges),
        )

    def health(self) -> HealthView:
        return HealthView(
            status="ok",
            openai_enabled=self.settings.openai_enabled,
            node_count=len(self.use_case.nodes),
            edge_count=len(self.use_case.edges),
        )

    def summary(self) -> SummaryView:
        use_case_view = self._use_case_view()
        return SummaryView(
            use_case=use_case_view,
            node_count=len(self.use_case.nodes),
            edge_count=len(self.use_case.edges),
        )

    def use_case_view(self) -> UseCaseView:
        return self._use_case_view()

    def investigate(self, question: str, mode: str = "compare", top_k: int = 8) -> InvestigationResponse:
        graph_view = None
        vector_view = None

        if mode in {"compare", "graph"}:
            graph_retrieval = self.index.retrieve(question, mode="graph", top_k=top_k)
            graph_answer = self.answer_generator.generate(question, graph_retrieval, self.index, self.use_case)
            graph_view = self._mode_view(graph_retrieval, graph_answer)

        if mode in {"compare", "vector"}:
            vector_retrieval = self.index.retrieve(question, mode="vector", top_k=top_k)
            vector_answer = self.answer_generator.generate(question, vector_retrieval, self.index, self.use_case)
            vector_view = self._mode_view(vector_retrieval, vector_answer)

        comparison = None
        if graph_view and vector_view:
            graph_only = {
                evidence.node.id for evidence in graph_view.retrieval.evidence
            } - {evidence.node.id for evidence in vector_view.retrieval.evidence}
            graph_only_names = [self.index.nodes[node_id].name for node_id in sorted(graph_only)]
            comparison = (
                "Graph retrieval adds connected investigation context beyond the vector baseline. "
                f"In this query it surfaced: {', '.join(graph_only_names[:4]) or 'no additional entities beyond the baseline'}."
            )

        return InvestigationResponse(
            question=question,
            use_case=self._use_case_view(),
            graph=graph_view,
            vector=vector_view,
            comparison=comparison,
        )

    def _mode_view(
        self,
        retrieval: RetrievalOutcome,
        answer: AnswerOutcome,
    ) -> InvestigationModeView:
        sub_nodes, sub_edges = self.index.subgraph(retrieval)
        return InvestigationModeView(
            retrieval=RetrievalView(
                mode=retrieval.mode,
                explanation=retrieval.explanation,
                cypher_preview=retrieval.cypher_preview,
                query_entity_ids=list(retrieval.query_entity_ids),
                evidence=[
                    self._evidence_view(candidate)
                    for candidate in retrieval.candidates
                ],
                subgraph_nodes=[self._node_view(node) for node in sub_nodes],
                subgraph_edges=[self._edge_view(edge) for edge in sub_edges],
                paths=[
                    PathView(
                        node_ids=list(path.node_ids),
                        node_names=[self.index.nodes[node_id].name for node_id in path.node_ids],
                        edge_types=list(path.edge_types),
                        narrative=path.narrative,
                    )
                    for path in retrieval.paths
                ],
                metrics=retrieval.metrics,
            ),
            answer=AnswerView(
                answer=answer.answer,
                key_points=list(answer.key_points),
                recommended_actions=list(answer.recommended_actions),
                graph_value=answer.graph_value,
                limitations=list(answer.limitations),
                provider=answer.provider,
            ),
        )

    def _use_case_view(self) -> UseCaseView:
        entity_counts = Counter(node.kind for node in self.use_case.nodes)
        relationship_counts = Counter(edge.type for edge in self.use_case.edges)
        return UseCaseView(
            id=self.use_case.id,
            title=self.use_case.title,
            description=self.use_case.description,
            learning_goals=list(self.use_case.learning_goals),
            storyline=list(self.use_case.storyline),
            suggested_questions=list(self.use_case.suggested_questions),
            entity_counts=dict(sorted(entity_counts.items())),
            relationship_counts=dict(sorted(relationship_counts.items())),
        )

    def _node_view(self, node: GraphNode) -> NodeView:
        return NodeView(
            id=node.id,
            kind=node.kind,
            name=node.name,
            description=node.description,
            stage=node.stage,
            tags=list(node.tags),
        )

    def _edge_view(self, edge: GraphEdge) -> EdgeView:
        return EdgeView(
            source=edge.source,
            target=edge.target,
            type=edge.type,
            description=edge.description,
            weight=edge.weight,
        )

    def _evidence_view(self, candidate) -> EvidenceView:
        node = self.index.nodes[candidate.node_id]
        return EvidenceView(
            node=self._node_view(node),
            score=candidate.score,
            reasons=list(candidate.reasons),
            hop_distance=None if candidate.hop_distance == float("inf") else candidate.hop_distance,
            seed=candidate.seed,
        )

