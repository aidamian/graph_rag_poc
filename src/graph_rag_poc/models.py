from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _metadata_text(metadata: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in metadata.items():
        if isinstance(value, (list, tuple)):
            rendered = " ".join(str(item) for item in value)
        else:
            rendered = str(value)
        parts.append(f"{key} {rendered}")
    return " ".join(parts)


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str
    name: str
    description: str
    aliases: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    stage: str = "context"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def retrieval_text(self) -> str:
        return " ".join(
            part
            for part in [
                self.name,
                self.kind,
                self.description,
                " ".join(self.aliases),
                " ".join(self.tags),
                self.stage,
                _metadata_text(self.metadata),
            ]
            if part
        )


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    type: str
    description: str
    weight: float = 1.0


@dataclass(frozen=True)
class UseCase:
    id: str
    title: str
    description: str
    learning_goals: tuple[str, ...]
    storyline: tuple[str, ...]
    suggested_questions: tuple[str, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def with_snapshot(
        self,
        nodes: tuple[GraphNode, ...],
        edges: tuple[GraphEdge, ...],
    ) -> "UseCase":
        return UseCase(
            id=self.id,
            title=self.title,
            description=self.description,
            learning_goals=self.learning_goals,
            storyline=self.storyline,
            suggested_questions=self.suggested_questions,
            nodes=nodes,
            edges=edges,
        )


@dataclass(frozen=True)
class RetrievalCandidate:
    node_id: str
    score: float
    reasons: tuple[str, ...]
    hop_distance: int = 0
    seed: bool = False


@dataclass(frozen=True)
class PathInsight:
    node_ids: tuple[str, ...]
    edge_types: tuple[str, ...]
    narrative: str


@dataclass(frozen=True)
class RetrievalOutcome:
    mode: str
    question: str
    query_entity_ids: tuple[str, ...]
    candidates: tuple[RetrievalCandidate, ...]
    paths: tuple[PathInsight, ...]
    explanation: str
    cypher_preview: str
    metrics: dict[str, Any]


@dataclass(frozen=True)
class AnswerOutcome:
    mode: str
    answer: str
    key_points: tuple[str, ...]
    recommended_actions: tuple[str, ...]
    graph_value: str
    limitations: tuple[str, ...]
    provider: str

