# Graph RAG Cybersecurity PoC Spec

Last updated: 2026-03-18

Status: reconstructed from the user prompt because the referenced original `graph_rag_poc.md` was not present in the repository history.

## Goal

Implement an end-to-end proof of concept that demonstrates how Graph RAG can support AI-augmented cybersecurity investigation.

## Audience

- Data scientists who need an understandable, inspectable example of Graph RAG.
- IT security practitioners who need to see how graphs plus AI can improve triage, investigation, and response reasoning.

## Core Demonstration Requirements

1. The system must ingest a cybersecurity knowledge set into a graph database.
2. The system must answer investigation questions using graph-aware retrieval.
3. The system must expose retrieval evidence so users can understand why the answer was produced.
4. The system must include a realistic cybersecurity use case.
5. The system must be containerized and runnable locally.
6. The system must have tests and detailed logs.
7. The repository must include clear instructions and concise educational explanations.

## Functional Scope

### Data Layer

- Seed a demo cybersecurity knowledge graph.
- Use realistic entities such as threat actors, campaigns, techniques, vulnerabilities, alerts, assets, controls, and supporting documents.
- Make it clear which parts are synthetic or reconstructed for demonstration.

### Retrieval Layer

- Implement a baseline vector-style retrieval path for comparison.
- Implement a graph-aware retrieval path that expands from seed entities through meaningful relationships.
- Return both evidence items and the graph paths that connect them.

### Generation Layer

- Produce investigation-oriented answers grounded in retrieved evidence.
- Support OpenAI-backed generation when credentials are available.
- Provide a deterministic offline fallback so tests and demos still run without external secrets.

### API Layer

- Expose endpoints for health, graph summary, seed/reset, question answering, and use-case exploration.
- Return retrieval traces and supporting evidence in structured JSON.

### UI Layer

- Provide a simple but polished interface for:
  - understanding the use case,
  - running questions,
  - comparing Graph RAG vs vector-only retrieval,
  - inspecting graph evidence and recommended actions.

## Non-Goals

- Production-scale ingestion.
- Real customer data.
- Autonomous response actions.
- Fine-tuning or multi-tenant security hardening.

## Use-Case Requirement

The PoC must include at least one coherent incident storyline showing why graph retrieval is useful. The preferred storyline is:

- public-facing exploit or phishing entry,
- execution and credential access,
- lateral movement,
- data staging or exfiltration,
- business-impact event,
- controls and recommended containment actions.

## Logging Requirement

The system must emit high-detail, colorized logs that separate:

- ingest activity,
- graph operations,
- retrieval activity,
- answer generation,
- API requests,
- UI requests.

## Testing Requirement

At minimum:

- unit tests for retrieval behavior,
- API tests for the core question-answer flow,
- one end-to-end smoke verification with containers.

## Acceptance Criteria

The PoC is acceptable when:

1. `docker compose up --build` starts the demo stack.
2. The graph can be seeded without manual database work.
3. A user can submit a cybersecurity investigation question and receive:
   - an answer,
   - evidence,
   - graph context,
   - recommended next actions.
4. The user can compare graph-aware retrieval with a vector-only baseline.
5. The logs make it possible to inspect how retrieval and answer synthesis behaved.
6. The repo contains `AGENTS.md`, `PLAN.md`, and an updated `README.md`.

