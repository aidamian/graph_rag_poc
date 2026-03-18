from fastapi.testclient import TestClient

from graph_rag_poc.config import Settings
from graph_rag_poc.service import GraphRagService
from services.api.main import create_app


def build_client() -> TestClient:
    settings = Settings(use_openai="never")
    service = GraphRagService(settings=settings)
    app = create_app(service=service, settings=settings)
    return TestClient(app)


def test_summary_endpoint_returns_use_case_metadata() -> None:
    client = build_client()
    response = client.get("/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_count"] > 0
    assert payload["use_case"]["title"] == "Operation Night Lantern"


def test_ask_endpoint_returns_comparison_payload() -> None:
    client = build_client()
    response = client.post(
        "/ask",
        json={
            "question": "How are the VPN exploit alerts connected to the ransomware on fs-02?",
            "mode": "compare",
            "top_k": 6,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["graph"] is not None
    assert payload["vector"] is not None
    assert payload["comparison"] is not None
    assert payload["graph"]["retrieval"]["paths"]
