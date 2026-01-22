# Roadmap and Milestones

## Context / Why
This PoC is the first stage of a longer roadmap toward a competitive inference network.
This document defines milestones and a clear Definition of Done (DoD) for the PoC.

## Goals
- Provide an execution plan with clear milestones.
- Define PoC DoD and handoff criteria.

## Non-goals
- Detailed staffing or budget planning.
- Production SLOs.

## Functional requirements
- Roadmap includes: MVP build, baseline competitor, benchmark suite, guardrails, demo.
- Each milestone has measurable outcomes.

## Non-functional requirements
- Milestones should fit within a short PoC timeline (2-4 weeks).

## API/contracts
- Not applicable.

## Data flow
- Not applicable.

## Milestones
1) **M0: Specs Complete**
   - All spec files written and reviewed.
   - OpenAPI specs validated.

2) **M1: Gateway + UI Skeleton**
   - Gateway provides `/v1/chat/completions` and `/health`.
   - UI can send a prompt and render streaming output.

3) **M2: Baseline Competitor**
   - Fast-path chat works without sandbox.
   - Complex-path uses Sandy and emits artifacts.

4) **M3: Benchmark Harness**
   - CLI runs public/dev suite and outputs scores.
   - Streaming continuity metrics collected.

5) **M4: Demo + Hardening**
  - End-to-end demo with UI, gateway, baseline.
  - Guardrail enforcement documented and partially implemented.
  - Generate implementation README + architecture diagrams.

## Definition of Done (PoC)
- UI, Gateway, and Baseline competitor are running locally.
- OpenAI-compatible streaming works end-to-end.
- At least one artifact-producing task is demonstrated.
- Bench runner outputs a composite score from a public/dev suite.
- Guardrails are documented and minimal enforcement exists.
 - Documentation deliverables (README + diagrams) are produced.

## Acceptance criteria
- Milestones are concrete and testable.
- DoD is unambiguous.

## Open questions / risks
- Should we include a minimal hosted demo for PoC, or local-only?
