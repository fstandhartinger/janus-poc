# Spec 23: Landing Page Copy & Branding Fixes

## Status: COMPLETE

## Context

The landing page needs copy and branding updates to align with Jon's vision of "open intelligence" rather than "AI agents". The current copy uses "agent" terminology which pigeonholes the vision. Additionally, there are visual bugs and branding inconsistencies to fix.

## Requirements

### 23.1 Visual Bug Fixes

#### 23.1.1 How It Works Step Numbers
- The circle with "2" is hidden behind the horizontal connecting line
- Fix z-index so step number circles appear ABOVE the connecting lines
- All step circles (1, 2, 3) should be visually on top of the lines

### 23.2 Terminology Changes: "Agent" → "Intelligence"

Replace all occurrences of "agent" terminology with "intelligence" or "engine":

| Current | Replace With |
|---------|--------------|
| "build the best AI agent" | "build the best intelligence engine" |
| "Your agent handles it all" | "Your Janus engine handles it all" |
| "AI agent" (anywhere) | "intelligence engine" or "Janus submission" |
| "Miner Rodeo" | "Intelligence Rodeo" or just "Rodeo" |

### 23.3 Specific Copy Changes

#### 23.3.1 Benchmarks Description
Change:
> "Benchmarks score implementations on composite metrics: quality, speed, cost"

To:
> "Benchmarks score implementations on many use cases and composite metrics: quality, speed, cost"

#### 23.3.2 Button Text
- Change "Try Manus Chat" → "Try Janus Chat" (if not already fixed)

### 23.4 Powered By Section

Keep only:
- ✅ Chutes
- ✅ Bittensor (rename from "Bittensor Subnet 64")

Remove:
- ❌ OpenAI Compatible
- ❌ Sandy Sandboxes

### 23.5 Footer Updates

#### 23.5.1 Copyright
Change:
> © 2026 Janus

To:
> © 2026 Chutes.ai

#### 23.5.2 Social Links
- Twitter/X: `https://x.com/chutes_ai`
- GitHub: `https://github.com/chutesai`

### 23.6 Add Decentralization Idealism Section

Add a new section (or integrate into existing copy) that highlights the Bittensor ethos:

**Key themes to convey:**
- **Decentralized**: No single point of control or failure
- **Permissionless**: Anyone can participate without approval
- **Affordable**: Fair pricing through open competition
- **Open Source**: Transparent, auditable, forkable
- **No Gatekeepers**: No corporate overlords deciding who can build
- **Censorship Resistant**: Resilient against authoritarian restrictions
- **Community Owned**: Value flows to contributors, not shareholders

**Suggested copy block:**
```
## Built on Bittensor Ideals

Janus isn't just another AI platform — it's a return to the original promise of the internet: open, permissionless, and owned by no one.

- **Decentralized** — No single company controls the network
- **Permissionless** — Anyone can compete, no approval needed
- **Open Source** — All code is transparent and auditable
- **Censorship Resistant** — No government can shut it down
- **Community Driven** — Rewards flow to builders, not shareholders

We believe intelligence should be a public utility, not a corporate moat.
```

### 23.7 Flexibility & Openness Messaging

Add messaging that clarifies Janus submissions aren't limited to one framework:

**Suggested addition to "How It Works" or a new section:**
```
## Any Stack. Any Approach.

Your Janus submission can be built with:
- CLI agents (Claude Code, Aider, OpenHands)
- Workflow engines (n8n, LangGraph, CrewAI)
- Custom model orchestration
- Simple model switchers
- Complex multi-agent systems

As long as it speaks the OpenAI-compatible API and streams reasoning, you're in.
```

### 23.8 Marketplace Clarification

Update the marketplace/components messaging:

Change from generic "Build & Earn" to:
> "Publish reusable components (research nodes, tools, memory systems). Earn rewards whenever another Janus submission uses your component."

### 23.9 Security/Fairness Note (Optional)

Consider adding:
> "Network access and tool usage are sandboxed and controlled. Miners get whitelisted services (proxy search, vector index, sandbox API) ensuring security and fair competition."

## Acceptance Criteria

### Visual
- [ ] Step number circles (1, 2, 3) appear above connecting lines
- [ ] No z-index visual bugs in How It Works section

### Copy
- [ ] No instances of "AI agent" - all replaced with "intelligence engine" or similar
- [ ] "Manus" replaced with "Janus" everywhere
- [ ] Benchmarks description updated with "many use cases"
- [ ] "Miner Rodeo" renamed to "Intelligence Rodeo" or "Rodeo"

### Powered By
- [ ] Only shows: Chutes, Bittensor
- [ ] Does NOT show: OpenAI Compatible, Sandy Sandboxes

### Footer
- [ ] Copyright says "© 2026 Chutes.ai"
- [ ] Twitter links to https://x.com/chutes_ai
- [ ] GitHub links to https://github.com/chutesai

### Idealism
- [ ] Decentralization/Bittensor ethos section exists
- [ ] Conveys: permissionless, open source, censorship resistant, community owned

### Flexibility
- [ ] Messaging clarifies any stack/approach works
- [ ] Lists examples: CLI agents, workflow engines, custom orchestration

## Files to Update

- `ui/src/app/page.tsx` or `ui/src/components/landing/` components
- `ui/src/components/landing/HowItWorks.tsx` - z-index fix
- `ui/src/components/landing/PoweredBy.tsx` - remove items
- `ui/src/components/landing/Footer.tsx` - copyright and links
- `ui/src/components/landing/HeroSection.tsx` - terminology

## Research

Before implementing, research Bittensor's core philosophy:
- Read https://bittensor.com/ for their messaging
- Check Bittensor whitepaper for decentralization ideals
- Look at how they describe permissionless, open, censorship-resistant networks

## Notes

This spec aligns with Jon's vision that Janus is an "open intelligence platform" not an "agent framework". The terminology shift from "agent" to "intelligence" is intentional and important for positioning.

The Bittensor idealism section should feel authentic, not preachy. It should resonate with crypto-native builders who value decentralization.
