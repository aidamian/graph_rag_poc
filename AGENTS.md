# AGENTS.md

Last updated: 2026-03-18

This file defines how coding agents should work in this repository.

## Mission

Build and maintain a containerized Graph RAG proof of concept for AI-augmented cybersecurity investigation. The repository must stay understandable for:

- Data scientists who want to learn how Graph RAG differs from vector-only RAG.
- IT security practitioners who want to see how graph retrieval and AI can support incident investigation and response.

## Default Execution Contract

1. Inspect before editing.
2. Restate the task in concrete terms.
3. Produce or update a plan before substantial implementation.
4. Make the smallest coherent change that moves the task forward.
5. Verify with executable checks, not intent.
6. Record important assumptions in docs.
7. Leave the repo in a runnable state.

## Project Priorities

1. Correctness and reproducibility.
2. End-to-end operability with `docker compose`.
3. Educational clarity of the Graph RAG flow.
4. Strong observability: high-detail logs, visible retrieval traces, explicit evidence.
5. Polished developer ergonomics after correctness is stable.

## Source-of-Truth Hierarchy

When instructions conflict, prefer them in this order:

1. Direct user request.
2. This `AGENTS.md`.
3. `PLAN.md`.
4. Inline code comments and local conventions.

## Actor-Critic Workflow

Use this loop for non-trivial work. Keep each loop narrow.

### 1. Plan

- Define the exact outcome and the failing gap.
- Name impacted files and services.
- Define a concrete verification target before editing.
- Prefer one concern per loop.

### 2. Implement

- Change the smallest vertical slice that can be verified.
- Preserve existing behavior unless the task explicitly changes it.
- Prefer explicit code over clever abstraction.

### 3. Test

- Run the most local test first.
- Then run the nearest integration or end-to-end check.
- Capture environment feedback before making stylistic judgments.

### 4. Critique

- Diagnose from logs, traces, failing assertions, API responses, or rendered UI behavior.
- Critique one root concern at a time.
- Fix correctness, safety, data integrity, and integration issues before style or micro-optimizations.

### 5. Revise

- Apply one focused fix.
- Do not mix speculative cleanups into a repair loop.

### 6. Verify

- Re-run the exact failing check.
- Re-run adjacent smoke checks that could regress.
- Update docs if behavior or operations changed.

## Stop-And-Escalate Rules

Stop and escalate to the user with evidence if any of the following holds:

- Two focused loops failed on the same root cause without new evidence.
- Three total loops on one task produced no measurable progress.
- The missing information is external and cannot be inferred safely.
- The next step requires destructive data changes, secret access, billing impact, or production risk.
- The failure appears to be environmental or flaky rather than code-local.

When escalating, provide:

- What was attempted.
- Exact failing commands or symptoms.
- Current hypothesis.
- Two or three viable next options.

## Feedback Ordering

Always prioritize feedback in this order:

1. Environment and execution failures.
2. Data or schema correctness.
3. Retrieval quality and grounding.
4. API and UI behavior.
5. Performance and maintainability.
6. Style.

Do not spend a loop on style when the environment or retrieval path is still broken.

## Research And Prompting Guidance

These rules are synthesized from current OpenAI Codex documentation, OpenAI eval guidance, and recent agentic coding literature:

- Keep repository instructions concrete, short, and discoverable.
- Define success criteria and verification commands explicitly.
- Use bounded subtasks and preserve the main thread for integration decisions.
- Favor iterative eval-driven improvement over large speculative rewrites.
- Use narrow critiques and narrow graders rather than broad “make it better” prompts.
- Treat logs, traces, and failing tests as primary feedback signals.

See [docs/actor_critic_workflow.md](/home/andrei/work/graph_rag_poc/docs/actor_critic_workflow.md) for the supporting notes and source links.

## Repository Expectations

### Architecture

- Keep the PoC multi-service and containerized.
- Prefer simple Python services with explicit boundaries.
- Neo4j is the graph system of record unless a task explicitly changes that.

### Data

- Use safe demo data only.
- Clearly label synthetic or reconstructed cybersecurity artifacts.
- Keep the use case realistic enough to teach graph retrieval value.

### Logging

- Use structured, colorized logs for ingest, graph, retrieval, API, UI, and LLM activity.
- Log enough detail to debug retrieval quality without exposing secrets.

### Testing

- Add unit tests for retrieval logic and transformation rules.
- Add API-level tests for the main workflows.
- Keep an executable end-to-end smoke path for `docker compose`.

### Documentation

- Update `README.md` when setup, architecture, or usage changes.
- Keep `PLAN.md` aligned with implementation reality.
- Document tradeoffs, especially where the original spec had to be reconstructed.

## Change Discipline

- Do not rewrite large areas without a concrete reason.
- Do not silently invent hidden requirements.
- If the local repo is missing an expected artifact, document the reconstruction explicitly.
- When adding dependencies, justify them through user value or operational simplicity.

## Definition Of Done

The task is done only when all of the following are true:

- The PoC can be started with documented container commands.
- The graph is seeded automatically or through a documented command.
- A user can run at least one full cybersecurity Graph RAG investigation flow.
- Logs and retrieval evidence make the system behavior inspectable.
- Tests exist and have been run for the implemented scope.
- `README.md` explains what the system demonstrates and how to use it.

