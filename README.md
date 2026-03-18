# Cyber Graph RAG PoC

This repository contains a containerized proof of concept that demonstrates how Graph RAG can support AI-augmented cybersecurity investigation.

It is built to help two audiences quickly:

- Data scientists: understand how graph-aware retrieval differs from vector-only retrieval.
- IT security practitioners: see how alerts, assets, ATT&CK techniques, vulnerabilities, and controls can be connected into one investigation workflow.

## What The PoC Shows

- A synthetic ransomware investigation called `Operation Night Lantern`.
- A Neo4j-backed cybersecurity knowledge graph with 28 entities and 55 relationships.
- A FastAPI service that answers investigation questions in:
  - `vector` mode,
  - `graph` mode,
  - `compare` mode.
- A Streamlit UI that lets you compare Graph RAG against vector-only retrieval and inspect the returned subgraph.
- Detailed colorized logs for ingest, graph, retrieval, API, UI, and answer generation.
- An offline deterministic answer path, plus optional OpenAI-backed generation when `OPENAI_API_KEY` is provided.

## Architecture

- `neo4j`: graph system of record and browser.
- `api`: FastAPI service that seeds the graph, runs retrieval, and assembles grounded answers.
- `ui`: Streamlit app for interactive exploration and investigation.

The current demo use case follows this chain:

1. A public-facing PAN-OS GlobalProtect gateway is exposed through `CVE-2024-3400`.
2. The attacker pivots to `jump-01` and executes encoded PowerShell.
3. A valid service account is abused for RDP lateral movement to `fs-02`.
4. Data is staged to cloud storage and ransomware impacts the file server.
5. Graph-aware retrieval brings in the connected controls needed for containment.

## Run

Optional: create `.env` from `.env.example` if you want OpenAI-backed answer generation.

```bash
cp .env.example .env
docker compose up --build
```

Open:

- UI: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`
- Neo4j Browser: `http://localhost:7474`

Neo4j credentials:

- username: `neo4j`
- password: `graph-rag-demo`

## Typical Demo Flow

1. Open the UI.
2. Run `How are the VPN exploit alerts connected to the ransomware on fs-02?`
3. Compare the `Graph RAG` and `Vector Baseline` panels.
4. Inspect the `Graph View` and the connected paths.
5. Run `What should the SOC do in the next four hours to contain Operation Night Lantern?`

The graph mode should surface intermediate techniques and containment controls that the vector baseline does not preserve as cleanly.

## Test

Local tests:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Container smoke test:

```bash
docker compose up --build -d
./scripts/smoke_test.sh
```

## Useful Commands

Follow logs:

```bash
docker compose logs -f api ui neo4j
```

Reset the demo:

```bash
curl -X POST http://localhost:8000/admin/seed
```

Stop and remove containers:

```bash
docker compose down -v
```

## Repo Guide

- [AGENTS.md](/home/andrei/work/graph_rag_poc/AGENTS.md): repository rules and actor-critic workflow.
- [graph_rag_poc.md](/home/andrei/work/graph_rag_poc/graph_rag_poc.md): reconstructed spec for this PoC.
- [PLAN.md](/home/andrei/work/graph_rag_poc/PLAN.md): implementation plan and milestones.
- [docs/actor_critic_workflow.md](/home/andrei/work/graph_rag_poc/docs/actor_critic_workflow.md): research notes behind the repo workflow.

## Notes

- The original `graph_rag_poc.md` referenced in the prompt was not present in the repository history, so the spec in this repo was reconstructed from the task description.
- The cybersecurity data is synthetic by design. The objective is to teach Graph RAG mechanics, not to publish threat intelligence.
- Without `OPENAI_API_KEY`, the app still works end-to-end using a deterministic offline answer generator.
