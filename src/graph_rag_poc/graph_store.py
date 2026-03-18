from __future__ import annotations

import json
import time
from typing import Any

from neo4j import GraphDatabase

from graph_rag_poc.logging_utils import get_logger
from graph_rag_poc.models import GraphEdge, GraphNode, UseCase


class Neo4jGraphStore:
    def __init__(
        self,
        uri: str,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self.uri = uri
        self.database = database
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.logger = get_logger("GRAPH")

    def close(self) -> None:
        self.driver.close()

    def wait_until_ready(self, timeout_seconds: int = 60) -> None:
        deadline = time.time() + timeout_seconds
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with self.driver.session(database=self.database) as session:
                    session.run("RETURN 1 AS ok").single()
                self.logger.info("neo4j_ready", uri=self.uri, database=self.database)
                return
            except Exception as exc:  # pragma: no cover - exercised in integration smoke
                last_error = exc
                self.logger.info("neo4j_waiting", uri=self.uri, error=str(exc))
                time.sleep(2)
        raise RuntimeError(f"Neo4j was not ready after {timeout_seconds}s: {last_error}")

    def ensure_schema(self) -> None:
        queries = (
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE",
            "CREATE INDEX entity_kind IF NOT EXISTS FOR (n:Entity) ON (n.kind)",
            "CREATE INDEX entity_name IF NOT EXISTS FOR (n:Entity) ON (n.name)",
        )
        with self.driver.session(database=self.database) as session:
            for query in queries:
                session.run(query).consume()
        self.logger.info("schema_ready")

    def is_empty(self) -> bool:
        with self.driver.session(database=self.database) as session:
            record = session.run("MATCH (n:Entity) RETURN count(n) AS count").single()
        return bool(record and record["count"] == 0)

    def reset(self) -> None:
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n:Entity) DETACH DELETE n").consume()
        self.logger.info("graph_reset")

    def seed(self, use_case: UseCase, reset: bool = True) -> None:
        self.ensure_schema()
        if reset:
            self.reset()

        node_rows = [self._serialize_node(node) for node in use_case.nodes]
        edge_rows = [self._serialize_edge(edge) for edge in use_case.edges]

        with self.driver.session(database=self.database) as session:
            session.run(
                """
                UNWIND $rows AS row
                MERGE (n:Entity {id: row.id})
                SET n.kind = row.kind,
                    n.name = row.name,
                    n.description = row.description,
                    n.aliases = row.aliases,
                    n.tags = row.tags,
                    n.stage = row.stage,
                    n.metadata_json = row.metadata_json,
                    n.retrieval_text = row.retrieval_text
                """,
                rows=node_rows,
            ).consume()

            session.run(
                """
                UNWIND $rows AS row
                MATCH (s:Entity {id: row.source})
                MATCH (t:Entity {id: row.target})
                MERGE (s)-[r:RELATES_TO {source_id: row.source, target_id: row.target, type: row.type}]->(t)
                SET r.description = row.description,
                    r.weight = row.weight
                """,
                rows=edge_rows,
            ).consume()

        self.logger.info(
            "graph_seeded",
            nodes=len(node_rows),
            edges=len(edge_rows),
            use_case=use_case.id,
        )

    def load_snapshot(self) -> tuple[tuple[GraphNode, ...], tuple[GraphEdge, ...]]:
        with self.driver.session(database=self.database) as session:
            node_records = list(
                session.run(
                    """
                    MATCH (n:Entity)
                    RETURN n.id AS id,
                           n.kind AS kind,
                           n.name AS name,
                           n.description AS description,
                           n.aliases AS aliases,
                           n.tags AS tags,
                           n.stage AS stage,
                           n.metadata_json AS metadata_json
                    ORDER BY n.kind, n.name
                    """
                )
            )
            edge_records = list(
                session.run(
                    """
                    MATCH (s:Entity)-[r:RELATES_TO]->(t:Entity)
                    RETURN s.id AS source,
                           t.id AS target,
                           r.type AS type,
                           r.description AS description,
                           r.weight AS weight
                    ORDER BY r.type, s.id, t.id
                    """
                )
            )

        nodes = tuple(
            GraphNode(
                id=record["id"],
                kind=record["kind"],
                name=record["name"],
                description=record["description"],
                aliases=tuple(record["aliases"] or []),
                tags=tuple(record["tags"] or []),
                stage=record["stage"] or "context",
                metadata=json.loads(record["metadata_json"] or "{}"),
            )
            for record in node_records
        )
        edges = tuple(
            GraphEdge(
                source=record["source"],
                target=record["target"],
                type=record["type"],
                description=record["description"],
                weight=float(record["weight"] or 1.0),
            )
            for record in edge_records
        )
        return nodes, edges

    def counts(self) -> dict[str, Any]:
        with self.driver.session(database=self.database) as session:
            total_nodes = session.run("MATCH (n:Entity) RETURN count(n) AS count").single()["count"]
            total_edges = session.run(
                "MATCH (:Entity)-[r:RELATES_TO]->(:Entity) RETURN count(r) AS count"
            ).single()["count"]
            kind_rows = list(
                session.run(
                    """
                    MATCH (n:Entity)
                    RETURN n.kind AS kind, count(n) AS count
                    ORDER BY kind
                    """
                )
            )
        return {
            "node_count": total_nodes,
            "edge_count": total_edges,
            "kinds": {row["kind"]: row["count"] for row in kind_rows},
        }

    @staticmethod
    def _serialize_node(node: GraphNode) -> dict[str, Any]:
        return {
            "id": node.id,
            "kind": node.kind,
            "name": node.name,
            "description": node.description,
            "aliases": list(node.aliases),
            "tags": list(node.tags),
            "stage": node.stage,
            "metadata_json": json.dumps(node.metadata, sort_keys=True),
            "retrieval_text": node.retrieval_text,
        }

    @staticmethod
    def _serialize_edge(edge: GraphEdge) -> dict[str, Any]:
        return {
            "source": edge.source,
            "target": edge.target,
            "type": edge.type,
            "description": edge.description,
            "weight": edge.weight,
        }
