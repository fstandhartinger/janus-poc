# Competition Page Overhaul — Spec Index

## Status: DRAFT

## Overview

This folder contains specifications for overhauling the Janus Competition page at `janus.rodeo/competition`. The specs cover naming, framing, scoring, prize pool mechanics, submission requirements, architecture, and FAQ updates.

## Spec Files

| File | Title | Summary |
|------|-------|---------|
| [01_competition_overview.md](./01_competition_overview.md) | Naming & Framing | Rename to "The Rodeo", replace "agent" with "intelligence" |
| [02_description_and_scoring.md](./02_description_and_scoring.md) | Description & Scoring | New copy, expanded scoring categories, leaderboard columns |
| [03_steps_and_prize_pool.md](./03_steps_and_prize_pool.md) | Steps & Prize Pool | Five steps (Build, Evaluate, Submit, Compete, Earn), pool mechanism |
| [04_submission_and_open_source.md](./04_submission_and_open_source.md) | Submission & Open Source | What to submit, open source requirement, hotkey, review process |
| [05_architecture_overview.md](./05_architecture_overview.md) | Architecture | Request flow, platform services, security model, benchmarks |
| [06_faq_and_marketplace.md](./06_faq_and_marketplace.md) | FAQ & Marketplace | Updated FAQ, marketplace introduction |

## Key Themes

### 1. Intelligence, Not Agents
Replace all "agent" terminology with "intelligence implementation" or "intelligence engine". This is more inclusive of different approaches (model routers, workflow engines, multi-agent systems, etc.).

### 2. The Rodeo Brand
Tie the competition to the `janus.rodeo` domain with rodeo metaphors: The Rodeo, The Arena, Champion, etc.

### 3. Prize Pool Mechanism
Daily revenue → Prize pool → Accumulates while same #1 → New #1 claims all → Reset. Creates continuous incentive for improvement.

### 4. Open Source Requirement
All submissions must be open source (OSI-approved license). This enables community learning and incremental improvement.

### 5. Bittensor Integration
Submissions require a Bittensor hotkey for attribution and payout. Future integration with Subnet 64.

### 6. Clear Architecture
Explain the flow: User → Gateway → TEE Container → Platform Services. Document whitelisted services and security model.

### 7. Marketplace Preview
Introduce component marketplace where developers earn when their components are used by winning implementations.

## Implementation Order

Recommended order for implementation:

1. **Phase 1**: Terminology and copy changes (specs 01, 02)
2. **Phase 2**: Steps and prize pool UI (spec 03)
3. **Phase 3**: Submission form updates (spec 04)
4. **Phase 4**: Architecture diagrams (spec 05)
5. **Phase 5**: FAQ and marketplace section (spec 06)

## Dependencies

- Landing page terminology changes (spec 23) should be done first for consistency
- Prize pool backend infrastructure needed before pool display
- Marketplace is Phase 2 scope (preview only in Phase 1)

## Open Questions

See individual specs for detailed open questions. Key cross-cutting concerns:

1. **Prize pool economics**: What percentage of revenue goes to pool?
2. **Component valuation**: How to determine component contribution to winning?
3. **Decentralized review**: Timeline and mechanism for replacing manual review?
4. **TEE infrastructure**: Which provider? SLA? GPU support timeline?
