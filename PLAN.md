# PLAN.md

Last updated: 2026-03-18

Status: active implementation plan derived from [graph_rag_poc.md](/home/andrei/work/graph_rag_poc/graph_rag_poc.md).

## Delivery Strategy

Build the PoC in thin vertical slices:

1. Lock repo instructions and workflow.
2. Reconstruct the missing spec.
3. Build the graph-backed API and seeded use case.
4. Add the UI and comparison flow.
5. Add tests and end-to-end verification.
6. Tighten docs and usability.

## Required Steps

The plan explicitly covers the requested sequence:

1. Create a powerful `AGENTS.md` grounded in current OpenAI Codex guidance and adjacent best practices.
2. Research and encode a state-of-the-art plan -> implement -> test -> critique -> revise -> verify loop.
3. Encode the actor-critic workflow for repository use.
4. Prepare this implementation plan.
5. Review the spec and plan before implementation.
6. Implement the specs within containerized apps and services.
7. Test the PoC and add detailed colorized logs.
8. Create and refine the PoC cybersecurity use case.
9. Re-test and iterate until the core demo works cleanly.
10. Present final results and run instructions in `README.md`.

## Planned Architecture

- `neo4j`: graph database and browser.
- `api`: FastAPI service for seed, retrieval, and answer generation.
- `ui`: Streamlit interface for interactive investigation and explanation.

## Implementation Milestones

### Milestone 1: Shared foundations

- Create Python package layout.
- Add configuration, logging, data models, and seed dataset.
- Add Dockerfiles and compose topology.

### Milestone 2: Graph and retrieval

- Implement Neo4j schema/bootstrap.
- Implement baseline vector retrieval.
- Implement graph-aware retrieval with neighborhood expansion and path extraction.
- Implement answer assembly and offline fallback.

### Milestone 3: Application surfaces

- Expose API endpoints.
- Build UI with:
  - overview,
  - question form,
  - Graph RAG vs vector-only comparison,
  - evidence display,
  - graph visualization.

### Milestone 4: Verification

- Add unit and API tests.
- Run containerized smoke verification.
- Refine the use case and logs based on failures.

### Milestone 5: Documentation

- Write a concise educational README.
- Document tradeoffs and known limitations.

## Review Before Implementation

The reconstructed spec is internally consistent and feasible in this repo, but there is one explicit caveat:

- The original spec file referenced by the user was missing locally, so the scope above is inferred from the prompt. The implementation should therefore bias toward clarity, demonstrability, and safe defaults over undocumented extra features.

## Exit Criteria

- All acceptance criteria from [graph_rag_poc.md](/home/andrei/work/graph_rag_poc/graph_rag_poc.md) are met.
- Tests are present and executed.
- The default demo path works without requiring external credentials.
