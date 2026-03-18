# Actor-Critic Workflow Notes

Last updated: 2026-03-18

This document records the workflow adopted for this repository and the external material used to shape it.

## Adopted Workflow

For each substantial task, use:

1. Plan
2. Implement
3. Test
4. Critique
5. Revise
6. Verify

Operational rules:

- Keep one primary concern per loop.
- Let environment feedback lead the next action.
- Do not spend repair cycles on style while execution is still failing.
- Escalate after repeated failed loops instead of hiding uncertainty.

## Why This Workflow

### OpenAI Codex Guidance

- OpenAI’s current Codex docs emphasize concise repository instructions, explicit verification, and workflows that separate planning, implementation, and verification.
- The Codex best-practices and workflows pages push bounded work, clear constraints, and repeatable validation rather than vague large-step prompting.
- OpenAI’s eval guidance recommends reproducible evaluation, trace-level inspection, and iterative improvement loops.

Inference applied in this repository:

- “One concern per loop” is an implementation choice derived from OpenAI’s emphasis on narrow evaluation and bounded work. It is not a direct quote from a single page.
- “Environment feedback before style” is a practical ordering derived from OpenAI’s verification-first workflow guidance and agent-eval emphasis.

### Adjacent State-Of-The-Art Signals

- `Self-Refine` showed that iterative self-feedback can improve task quality when critique and revision are explicit.
- `Reflexion` and later agentic reflection work reinforced the value of verbal feedback plus retry loops.
- `A Self-Improving Coding Agent` argues that reflection plus code changes can improve coding-agent performance, but repeated ineffective loops should be treated as a system signal, not as a reason to continue blindly.

Inference applied in this repository:

- The stop-and-escalate rule is a safety rail added on top of the literature, not something claimed verbatim by a source.

## Practical Loop Template

Use the following pattern in implementation sessions:

1. `Plan`: define the target behavior and the exact check that proves it.
2. `Implement`: make one focused change.
3. `Test`: run the narrowest executable check.
4. `Critique`: isolate the highest-value failure.
5. `Revise`: fix only that concern.
6. `Verify`: rerun the failing check and a nearby smoke test.

## Escalation Thresholds

Escalate when:

- Two attempts failed on the same root cause.
- Three loops produced no measurable progress.
- Required context is missing and unsafe to guess.
- The next action has destructive or external side effects.

## Sources

- OpenAI Models: https://developers.openai.com/api/docs/models
- OpenAI Codex landing/docs hub: https://developers.openai.com/
- OpenAI Codex Workflows: https://developers.openai.com/codex/workflows
- OpenAI Codex Best Practices: https://developers.openai.com/codex/learn/best-practices
- OpenAI Codex Prompting Guide: https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide
- OpenAI Reasoning Best Practices: https://developers.openai.com/api/docs/guides/reasoning-best-practices
- OpenAI Agent Evals: https://developers.openai.com/api/docs/guides/agent-evals
- OpenAI Optimizing LLM Accuracy: https://developers.openai.com/api/docs/guides/optimizing-llm-accuracy
- Self-Refine: https://arxiv.org/abs/2303.17651
- Reflexion: https://arxiv.org/abs/2303.11366
- A Self-Improving Coding Agent: https://arxiv.org/abs/2504.15228

