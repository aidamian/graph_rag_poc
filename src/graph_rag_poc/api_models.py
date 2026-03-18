from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: str = Field(min_length=8)
    mode: Literal["compare", "graph", "vector"] = "compare"
    top_k: int = Field(default=8, ge=4, le=12)


class NodeView(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    stage: str
    tags: list[str]


class EdgeView(BaseModel):
    source: str
    target: str
    type: str
    description: str
    weight: float


class EvidenceView(BaseModel):
    node: NodeView
    score: float
    reasons: list[str]
    hop_distance: int | None = None
    seed: bool


class PathView(BaseModel):
    node_ids: list[str]
    node_names: list[str]
    edge_types: list[str]
    narrative: str


class RetrievalView(BaseModel):
    mode: str
    explanation: str
    cypher_preview: str
    query_entity_ids: list[str]
    evidence: list[EvidenceView]
    subgraph_nodes: list[NodeView]
    subgraph_edges: list[EdgeView]
    paths: list[PathView]
    metrics: dict[str, Any]


class AnswerView(BaseModel):
    answer: str
    key_points: list[str]
    recommended_actions: list[str]
    graph_value: str
    limitations: list[str]
    provider: str


class InvestigationModeView(BaseModel):
    retrieval: RetrievalView
    answer: AnswerView


class UseCaseView(BaseModel):
    id: str
    title: str
    description: str
    learning_goals: list[str]
    storyline: list[str]
    suggested_questions: list[str]
    entity_counts: dict[str, int]
    relationship_counts: dict[str, int]


class SummaryView(BaseModel):
    use_case: UseCaseView
    node_count: int
    edge_count: int


class SeedView(BaseModel):
    status: str
    node_count: int
    edge_count: int


class HealthView(BaseModel):
    status: str
    openai_enabled: bool
    node_count: int
    edge_count: int


class InvestigationResponse(BaseModel):
    question: str
    use_case: UseCaseView
    graph: InvestigationModeView | None = None
    vector: InvestigationModeView | None = None
    comparison: str | None = None

