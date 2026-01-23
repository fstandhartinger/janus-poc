# Spec 50: Why Janus Section - Audience Clarity

## Status: DRAFT

## Context / Why

The current "Why Janus?" section on the landing page mixes two distinct target audiences:

1. **Users** - People who use Janus to accomplish tasks (chat, research, content generation)
2. **Miners** - Developers who build and submit improved Janus implementations for rewards

Current cards:
- "Anything In, Anything Out" → User-focused
- "Intelligence Rodeo" → Miner-focused
- "Build & Earn" → Miner-focused

This creates confusion because visitors don't immediately understand which benefits apply to them.

## Goals

- Clearly distinguish user benefits from miner/developer benefits
- Help visitors quickly identify relevant value propositions
- Maintain visual appeal and consistency with design system

## Non-Goals

- Complete section redesign
- Adding new benefit cards
- Changing the core messaging

## Functional Requirements

### FR-1: Split into Two Audience Groups

Restructure the section to clearly separate audiences:

```
Why Janus?
The next generation of competitive intelligence infrastructure

┌─────────────────────────────────────────────────────┐
│  FOR USERS                                          │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ Anything In,    │  │ Always Improving│          │
│  │ Anything Out    │  │                 │          │
│  │ ...             │  │ ...             │          │
│  └─────────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  FOR BUILDERS                                       │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐          │
│  │ Intelligence    │  │ Build & Earn    │          │
│  │ Rodeo          │  │                 │          │
│  │ ...             │  │ ...             │          │
│  └─────────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────┘
```

### FR-2: Updated Card Content

**For Users Section:**

Card 1: "Anything In, Anything Out" (existing, keep as-is)
- Multimodal input (text, images, files) and multimodal output (text, code, images, artifacts). Your Janus engine handles it all.

Card 2: "Always Improving" (NEW - explain benefit of competition to users)
- A competitive marketplace of intelligence engines means you always get the best. Implementations are continuously benchmarked for quality, speed, and cost.

**For Builders Section:**

Card 1: "Intelligence Rodeo" (existing, reworded for clarity)
- Compete to build the best Janus implementation. Get benchmarked on quality, speed, and cost across diverse use cases. Top performers earn TAO rewards.

Card 2: "Build & Earn" (existing, keep similar)
- Create reusable components: research tools, memory systems, specialized agents. Earn rewards whenever your components power other submissions.

### FR-3: Visual Implementation

```tsx
// ui/src/components/landing/WhyJanusSection.tsx

export function WhyJanusSection() {
  return (
    <section className="why-janus-section">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-16" data-reveal>
          <h2 className="section-title">Why Janus?</h2>
          <p className="section-subtitle">
            The next generation of competitive intelligence infrastructure
          </p>
        </div>

        {/* For Users */}
        <div className="audience-group mb-12" data-reveal>
          <div className="audience-label">
            <span className="audience-badge user">For Users</span>
          </div>
          <div className="benefit-grid">
            <BenefitCard
              icon={<MultimodalIcon />}
              title="Anything In, Anything Out"
              description="Multimodal input (text, images, files) and multimodal output (text, code, images, artifacts). Your Janus engine handles it all."
            />
            <BenefitCard
              icon={<TrendingUpIcon />}
              title="Always Improving"
              description="A competitive marketplace of intelligence engines means you always get the best. Implementations are continuously benchmarked for quality, speed, and cost."
            />
          </div>
        </div>

        {/* For Builders */}
        <div className="audience-group" data-reveal>
          <div className="audience-label">
            <span className="audience-badge builder">For Builders</span>
          </div>
          <div className="benefit-grid">
            <BenefitCard
              icon={<TrophyIcon />}
              title="Intelligence Rodeo"
              description="Compete to build the best Janus implementation. Get benchmarked on quality, speed, and cost across diverse use cases. Top performers earn TAO rewards."
            />
            <BenefitCard
              icon={<ComponentIcon />}
              title="Build & Earn"
              description="Create reusable components: research tools, memory systems, specialized agents. Earn rewards whenever your components power other submissions."
            />
          </div>
        </div>
      </div>
    </section>
  );
}

interface BenefitCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function BenefitCard({ icon, title, description }: BenefitCardProps) {
  return (
    <div className="benefit-card">
      <div className="benefit-icon">{icon}</div>
      <h3 className="benefit-title">{title}</h3>
      <p className="benefit-description">{description}</p>
    </div>
  );
}
```

### FR-4: Styles

```css
/* ui/src/app/globals.css */

/* Why Janus Section */
.why-janus-section {
  background: var(--bg-secondary);
}

.audience-group {
  margin-bottom: 3rem;
}

.audience-label {
  margin-bottom: 1.5rem;
}

.audience-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.025em;
}

.audience-badge.user {
  background: rgba(99, 210, 151, 0.15);
  color: var(--accent-green);
  border: 1px solid rgba(99, 210, 151, 0.3);
}

.audience-badge.builder {
  background: rgba(250, 93, 25, 0.15);
  color: var(--accent-orange);
  border: 1px solid rgba(250, 93, 25, 0.3);
}

.benefit-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

@media (max-width: 768px) {
  .benefit-grid {
    grid-template-columns: 1fr;
  }
}

.benefit-card {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 1rem;
  padding: 1.5rem;
  transition: all 0.2s ease;
}

.benefit-card:hover {
  border-color: var(--accent-green);
  transform: translateY(-2px);
}

.benefit-icon {
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(99, 210, 151, 0.1);
  border-radius: 0.75rem;
  color: var(--accent-green);
  margin-bottom: 1rem;
}

.benefit-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

.benefit-description {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.6;
}
```

### FR-5: Alternative Layout (Compact)

If the split layout feels too heavy, an alternative using inline badges:

```tsx
<BenefitCard
  badge="For Users"
  badgeType="user"
  icon={<MultimodalIcon />}
  title="Anything In, Anything Out"
  description="..."
/>
```

Where each card has a small badge in the corner indicating the target audience.

## Non-Functional Requirements

### NFR-1: Accessibility

- Badges have sufficient color contrast
- Screen readers announce audience context
- All interactive elements keyboard accessible

### NFR-2: Responsiveness

- Stacks to single column on mobile
- Badges remain readable on all screen sizes

## Acceptance Criteria

- [ ] "For Users" and "For Builders" sections clearly separated
- [ ] Audience badges visually distinct (green for users, orange for builders)
- [ ] New "Always Improving" card explains user benefit of competition
- [ ] Responsive layout works on mobile
- [ ] Animation/reveal effects maintained
- [ ] Design system colors used correctly

## Files to Modify

```
ui/
└── src/
    ├── components/
    │   └── landing/
    │       └── WhyJanusSection.tsx  # MODIFY - Split by audience
    └── app/
        └── globals.css              # MODIFY - Add audience styles
```

## Related Specs

- `specs/18_landing_page.md` - Landing page implementation
- `specs/19_competition_page.md` - Competition details
