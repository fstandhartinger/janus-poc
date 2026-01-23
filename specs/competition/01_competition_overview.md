# Spec: Competition Overview – Naming & Framing

## Status: DRAFT

## Context / Why

The current Janus competition page uses terminology that positions the project as an "AI agent" framework. This framing is too narrow and pigeonholes the vision. Jon's vision is about **open intelligence** — building the best intelligence engine, not just "an agent." The competition should feel exciting, unique, and tied to the `janus.rodeo` domain and brand identity.

The word "agent" implies a specific architecture (agentic loops, tool use). In reality, Janus submissions can be anything: simple model switchers, complex multi-agent orchestrations, workflow engines, or novel approaches we haven't imagined. What matters is the quality of intelligence delivered through an OpenAI-compatible API.

## Goals

- Rename and reframe the competition section to emphasise **intelligence** over **agents**
- Tie the competition branding to the **Rodeo** theme (Janus riding the bull, competition as a rodeo)
- Create a memorable, distinctive identity that differentiates Janus from other AI competitions
- Use language that is inclusive of all implementation approaches

## Non-Goals

- Changing the underlying technical requirements (API compatibility, streaming, etc.)
- Redesigning the visual layout (covered in separate UI specs)
- Implementing prize pool mechanics (separate spec)

## Functional Requirements

### FR-1: Page Title and Headline

**Current:**
```
Janus Competition
Compete to build the best AI agent
```

**New:**
```
Janus Competition – The Rodeo
Compete to build the best intelligence engine
```

The subtitle "The Rodeo" ties into the `janus.rodeo` domain and the bull-riding imagery.

### FR-2: Terminology Replacement

Replace all instances of the following terms throughout the competition page:

| Current Term | Replace With |
|--------------|--------------|
| "AI agent" | "intelligence engine" or "Janus implementation" |
| "agent" (standalone) | "implementation" or "submission" |
| "build an agent" | "build an intelligence engine" |
| "your agent" | "your implementation" or "your Janus submission" |
| "miner's agent" | "miner's implementation" |
| "agent container" | "implementation container" or "Janus container" |

### FR-3: Rodeo Theme Integration

Incorporate rodeo metaphors where appropriate:

- **Competition** → **The Rodeo**
- **Leaderboard** → **The Arena** or **Rodeo Rankings**
- **Top performer** → **Champion** or **Top Bull Rider**
- **Competing** → **Riding in the Rodeo**
- **Prize pool** → **The Purse** (optional, rodeo term for prize money)

### FR-4: Taglines and Copy Snippets

Develop compelling taglines that reinforce the intelligence framing:

- "Where intelligence engines compete for supremacy"
- "Any stack. Any approach. One arena."
- "Build smarter, not just faster"
- "The decentralized intelligence competition"

### FR-5: Hero Section Copy

The hero section should immediately communicate:

1. This is a **competition** for building **intelligence engines**
2. It runs on the **Bittensor** decentralized network
3. **Anyone** can participate (permissionless)
4. There are **real rewards** for winning

Example hero copy:
```
# Janus Competition – The Rodeo

The decentralized arena where intelligence engines compete.
Build an OpenAI-compatible implementation. Score across
quality, speed, cost, and more. Rise to the top. Earn rewards.

No approval needed. No gatekeepers. Just your intelligence vs. the world.
```

## Non-Functional Requirements

### NFR-1: Tone and Voice

- **Bold**: Confident statements, not hedged language
- **Inclusive**: Welcome all approaches (CLI agents, workflow engines, simple routers)
- **Exciting**: This is a competition, convey energy and stakes
- **Decentralized ethos**: Emphasise permissionless, open, community-owned

### NFR-2: Consistency

All terminology changes must be applied consistently across:
- Competition page main copy
- FAQ section
- Documentation links
- Button labels and CTAs
- Meta descriptions and page titles

## API / Contracts

N/A – This spec covers copy and framing only.

## Acceptance Criteria

- [ ] Page title includes "The Rodeo" subtitle
- [ ] Headline uses "intelligence engine" instead of "AI agent"
- [ ] Zero instances of "AI agent" remain on the competition page
- [ ] Zero instances of standalone "agent" (referring to submissions) remain
- [ ] Rodeo theme is present in at least 2-3 places (title, section names, or copy)
- [ ] Hero copy communicates: competition, intelligence, Bittensor, permissionless, rewards
- [ ] Tone is bold, exciting, and inclusive of all implementation approaches

## Open Questions / Risks

1. **Brand consistency**: Does "The Rodeo" subtitle work across all contexts (emails, social, docs)?
2. **SEO impact**: Changing from "AI agent" may affect search discoverability — consider keeping "AI" in meta tags while using "intelligence" in visible copy
3. **Community reception**: Current users may be familiar with "agent" terminology — ensure transition is smooth

## Related Specs

- `02_description_and_scoring.md` – Expanded description and scoring model
- `specs/23_landing_copy_fixes.md` – Landing page terminology changes (parent spec)
