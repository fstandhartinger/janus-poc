# Component Marketplace (Phase 2)

## Status: COMPLETE

## Context / Why
Long term, Janus should support a marketplace where contributors submit reusable
components (e.g., "coding node", "research node") and earn rewards when used by miners.

## Goals
- Define the conceptual requirements for a component marketplace.
- Ensure interoperability via clear contracts (MCP tools, OpenAPI subservices).

## Non-goals
- Implementation in the PoC.
- Monetization or payout mechanics in detail.

## Functional requirements
- A component submission spec (manifest + API contract).
- Versioning and compatibility rules.
- Optional sandbox execution model for components.
- Attribution and usage tracking for reward splits.

## Non-functional requirements
- Components must be isolated from competitor core logic.
- Versioning must be deterministic and reproducible.

## API/contracts
- Components expose an MCP tool schema or OpenAPI contract.
- Components declare inputs/outputs and resource requirements.

### Example component manifest (Phase 2 concept)
```json
{
  "id": "cmp.research.web-search",
  "version": "0.1.0",
  "entrypoint": "https://components.janus.local/web-search",
  "contract": {
    "type": "openapi",
    "path": "/openapi.json"
  },
  "inputs": ["query", "top_k"],
  "outputs": ["results"],
  "resources": {
    "cpu": 1,
    "memory_mb": 512
  }
}
```

## Data flow
```mermaid
flowchart LR
  DEV[Component Developer] --> REG[Component Registry]
  REG --> COMP[Competitor]
  COMP -->|invoke| CMP[Component Service]
  CMP --> COMP
```

## Acceptance criteria
- Marketplace concept is fully specified with interfaces and versioning rules.
- Clear separation between PoC scope and Phase 2 goals.
- Example component manifest and contract are included in the spec appendix.

## Open questions / risks
- How to verify component safety and prevent data exfiltration?
- What governance model should decide reward splits?
