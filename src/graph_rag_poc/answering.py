from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from graph_rag_poc.logging_utils import get_logger
from graph_rag_poc.models import AnswerOutcome, GraphNode, RetrievalOutcome, UseCase
from graph_rag_poc.retrieval import KnowledgeGraphIndex


class DeterministicAnswerGenerator:
    def __init__(self) -> None:
        self.logger = get_logger("LLM")

    def generate(
        self,
        question: str,
        retrieval: RetrievalOutcome,
        index: KnowledgeGraphIndex,
        use_case: UseCase,
    ) -> AnswerOutcome:
        evidence_nodes = [index.nodes[candidate.node_id] for candidate in retrieval.candidates[:6]]
        selected_ids = {candidate.node_id for candidate in retrieval.candidates}
        controls = index.related_controls(selected_ids, limit=4)

        entry = self._first_by_stage(evidence_nodes, "initial-access")
        impact = self._first_by_stage(evidence_nodes, "impact")
        assets = [node.name for node in evidence_nodes if node.kind == "Asset"][:3]
        techniques = [node.name for node in evidence_nodes if node.kind == "Technique"][:4]

        path_sentence = retrieval.paths[0].narrative if retrieval.paths else "No short connected path was recovered from the current evidence subset."
        answer = (
            f"In {use_case.title}, the strongest grounded explanation is that the intrusion started with "
            f"{entry.name if entry else 'an exposed edge path'}, progressed through "
            f"{', '.join(techniques) if techniques else 'the observed attack chain'}, and reached "
            f"{impact.name if impact else 'the business-impact event'}. "
            f"The connected evidence chain is: {path_sentence}."
        )

        key_points = [
            f"Directly relevant assets: {', '.join(assets) if assets else 'the affected infrastructure in the retrieved subgraph'}.",
            f"Retrieved evidence covered {retrieval.metrics.get('candidate_count', 0)} entities and {retrieval.metrics.get('path_count', 0)} connected paths.",
            "The graph view keeps the exploit, execution, movement, exfiltration, and impact stages in one joined investigation trace.",
        ]
        if retrieval.mode == "vector":
            graph_value = (
                "Vector-only retrieval surfaces individually similar entities, but it does not explicitly preserve the connective path across stages."
            )
        else:
            graph_value = (
                "Graph-aware retrieval preserved the attack chain and pulled in connected controls, making the investigation easier to explain and act on."
            )

        recommended_actions = [
            f"{control.name}: {control.description}"
            for control in controls
        ] or [
            "Contain the impacted hosts and rotate exposed credentials.",
        ]

        limitations = (
            "This PoC uses a synthetic incident storyline for education.",
            "The answer is template-generated and grounded only in the retrieved demo graph.",
        )
        self.logger.info("deterministic_answer_generated", mode=retrieval.mode, question=question)
        return AnswerOutcome(
            mode=retrieval.mode,
            answer=answer,
            key_points=tuple(key_points),
            recommended_actions=tuple(recommended_actions),
            graph_value=graph_value,
            limitations=limitations,
            provider="offline-template",
        )

    @staticmethod
    def _first_by_stage(nodes: list[GraphNode], stage: str) -> GraphNode | None:
        for node in nodes:
            if node.stage == stage:
                return node
        return None


class OpenAIAnswerGenerator:
    def __init__(self, api_key: str, model: str, fallback: DeterministicAnswerGenerator) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.fallback = fallback
        self.logger = get_logger("LLM")

    def generate(
        self,
        question: str,
        retrieval: RetrievalOutcome,
        index: KnowledgeGraphIndex,
        use_case: UseCase,
    ) -> AnswerOutcome:
        payload = self._payload(question, retrieval, index, use_case)
        try:  # pragma: no cover - requires external API key
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "You are a cybersecurity investigation copilot. "
                                    "Ground every claim in the supplied evidence. "
                                    "Respond with strict JSON containing keys: "
                                    "answer, key_points, recommended_actions, graph_value, limitations."
                                ),
                            }
                        ],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": json.dumps(payload, indent=2)}],
                    },
                ],
            )
            data = json.loads(response.output_text)
            self.logger.info("openai_answer_generated", model=self.model, mode=retrieval.mode)
            return AnswerOutcome(
                mode=retrieval.mode,
                answer=data["answer"],
                key_points=tuple(data["key_points"]),
                recommended_actions=tuple(data["recommended_actions"]),
                graph_value=data["graph_value"],
                limitations=tuple(data["limitations"]),
                provider=f"openai:{self.model}",
            )
        except Exception as exc:  # pragma: no cover - exercised only when API call fails
            self.logger.warning("openai_answer_failed", error=str(exc), model=self.model)
            return self.fallback.generate(question, retrieval, index, use_case)

    @staticmethod
    def _payload(
        question: str,
        retrieval: RetrievalOutcome,
        index: KnowledgeGraphIndex,
        use_case: UseCase,
    ) -> dict[str, Any]:
        evidence = []
        for candidate in retrieval.candidates[:8]:
            node = index.nodes[candidate.node_id]
            evidence.append(
                {
                    "id": node.id,
                    "kind": node.kind,
                    "name": node.name,
                    "description": node.description,
                    "score": candidate.score,
                    "reasons": list(candidate.reasons),
                }
            )
        return {
            "question": question,
            "mode": retrieval.mode,
            "use_case": use_case.title,
            "storyline": list(use_case.storyline),
            "evidence": evidence,
            "paths": [path.narrative for path in retrieval.paths],
        }

