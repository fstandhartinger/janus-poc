# Spec 36: Janus UI Section in Bench Runner

## Status: DRAFT

## Context / Why

The chutes-bench-runner UI currently displays benchmarks in two categories:
- **Core Benchmarks** - Standard LLM benchmarks (MMLU-Pro, GPQA, HumanEval, etc.)
- **Affine Environments** - Specialized environment benchmarks

With the addition of Janus-specific benchmarks (research, tool use, multimodal, streaming, cost), we need a new **"Janus Intelligence"** section in the UI that:

1. Groups all Janus benchmarks together
2. Displays composite scoring breakdown
3. Shows Janus-specific metrics (TTFT, TPS, continuity)
4. Provides quick-select presets for Janus competition evaluation

## Goals

- Add "Janus Intelligence" category to benchmark-runner UI
- Display Janus benchmarks with their specific metrics
- Add composite score calculation and display
- Create "Janus Competition" preset for one-click evaluation
- Integrate with existing UI patterns

## Non-Goals

- Replacing existing benchmark categories
- Changing the core bench-runner architecture
- Implementing a separate Janus-only UI

## Functional Requirements

### FR-1: Backend Benchmark Metadata

Update benchmark registration to include category:

```python
# backend/app/benchmarks/adapters/janus_research.py

@register_adapter("janus_research")
class JanusResearchAdapter(BenchmarkAdapter):
    def get_name(self) -> str:
        return "janus_research"

    def get_display_name(self) -> str:
        return "Janus Research"

    def get_category(self) -> str:
        return "Janus Intelligence"

    def get_description(self) -> str:
        return "Web research, search, and synthesis capabilities"
```

### FR-2: API Response Schema

Update the `/api/benchmarks` response:

```typescript
interface Benchmark {
  name: string;
  display_name: string;
  category: string;          // "Core Benchmarks", "Janus Intelligence", etc.
  description: string;
  total_items: number;
  avg_item_latency_ms: number;
  is_enabled: boolean;
  default_selected: boolean;
  // Janus-specific fields
  janus_scoring_weight?: number;  // Weight in composite score
  janus_metrics?: string[];       // ["ttft", "tps", "continuity", etc.]
}
```

### FR-3: Frontend Category Display

Update `benchmark-runner.tsx` to display Janus category:

```typescript
// lib/api.ts - Add Janus category to order
const CATEGORY_ORDER = [
  "Core Benchmarks",
  "Janus Intelligence",  // NEW
  "Affine Environments"
];

// benchmark-runner.tsx - Group benchmarks by category
const benchmarksByCategory = useMemo(() => {
  const groups = new Map<string, Benchmark[]>();
  for (const benchmark of benchmarks) {
    const category = benchmark.category || "Core Benchmarks";
    if (!groups.has(category)) {
      groups.set(category, []);
    }
    groups.get(category)?.push(benchmark);
  }

  return Array.from(groups.entries()).sort(([a], [b]) => {
    const aIndex = CATEGORY_ORDER.indexOf(a);
    const bIndex = CATEGORY_ORDER.indexOf(b);
    if (aIndex !== -1 || bIndex !== -1) {
      return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
    }
    return a.localeCompare(b);
  });
}, [benchmarks]);
```

### FR-4: Janus Category Header

Add special header for Janus Intelligence section:

```tsx
// In benchmark-runner.tsx, within the category rendering

{category === "Janus Intelligence" && (
  <div className="mb-4 rounded-lg border border-moss/30 bg-moss/5 p-4">
    <div className="flex items-center justify-between">
      <div>
        <h4 className="text-sm font-semibold text-moss">
          Janus Competition Benchmarks
        </h4>
        <p className="mt-1 text-xs text-ink-400">
          These benchmarks measure research, tool use, multimodal, streaming, and cost efficiency.
          Results contribute to the Janus composite score.
        </p>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={() => selectJanusPreset()}
        className="border-moss/50 text-moss hover:bg-moss/10"
      >
        Select All Janus
      </Button>
    </div>

    {/* Composite Score Weights */}
    <div className="mt-3 grid grid-cols-5 gap-2 text-xs">
      <div className="text-center">
        <div className="font-semibold text-ink-200">Quality</div>
        <div className="text-moss">40%</div>
      </div>
      <div className="text-center">
        <div className="font-semibold text-ink-200">Speed</div>
        <div className="text-moss">20%</div>
      </div>
      <div className="text-center">
        <div className="font-semibold text-ink-200">Cost</div>
        <div className="text-moss">15%</div>
      </div>
      <div className="text-center">
        <div className="font-semibold text-ink-200">Streaming</div>
        <div className="text-moss">15%</div>
      </div>
      <div className="text-center">
        <div className="font-semibold text-ink-200">Modality</div>
        <div className="text-moss">10%</div>
      </div>
    </div>
  </div>
)}
```

### FR-5: Janus Preset Selection

Add function to select all Janus benchmarks:

```typescript
const JANUS_BENCHMARKS = [
  "janus_research",
  "janus_tool_use",
  "janus_multimodal",
  "janus_streaming",
  "janus_cost"
];

const selectJanusPreset = () => {
  setSelectedBenchmarks(prev => {
    const next = new Set(prev);
    // Add all Janus benchmarks
    for (const name of JANUS_BENCHMARKS) {
      if (benchmarks.some(b => b.name === name && b.is_enabled)) {
        next.add(name);
      }
    }
    return next;
  });
};
```

### FR-6: Janus Results Display

Display Janus-specific metrics in run results:

```tsx
// In run detail page or progress section

{isJanusRun && (
  <Card className="mt-4">
    <CardHeader>
      <CardTitle className="text-moss">Janus Composite Score</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="grid grid-cols-6 gap-4 text-center">
        <div>
          <div className="text-2xl font-bold text-moss">
            {formatPercent(compositeScore.composite)}
          </div>
          <div className="text-xs text-ink-400">Composite</div>
        </div>
        <div>
          <div className="text-xl text-ink-200">
            {formatPercent(compositeScore.quality)}
          </div>
          <div className="text-xs text-ink-400">Quality (40%)</div>
        </div>
        <div>
          <div className="text-xl text-ink-200">
            {formatPercent(compositeScore.speed)}
          </div>
          <div className="text-xs text-ink-400">Speed (20%)</div>
        </div>
        <div>
          <div className="text-xl text-ink-200">
            {formatPercent(compositeScore.cost)}
          </div>
          <div className="text-xs text-ink-400">Cost (15%)</div>
        </div>
        <div>
          <div className="text-xl text-ink-200">
            {formatPercent(compositeScore.streaming)}
          </div>
          <div className="text-xs text-ink-400">Streaming (15%)</div>
        </div>
        <div>
          <div className="text-xl text-ink-200">
            {formatPercent(compositeScore.modality)}
          </div>
          <div className="text-xs text-ink-400">Modality (10%)</div>
        </div>
      </div>

      {/* Streaming Metrics */}
      {streamingMetrics && (
        <div className="mt-4 grid grid-cols-4 gap-4 rounded-lg bg-ink-800/50 p-3">
          <div>
            <div className="text-sm font-medium text-ink-200">
              {streamingMetrics.avg_ttft_ms}ms
            </div>
            <div className="text-xs text-ink-400">Avg TTFT</div>
          </div>
          <div>
            <div className="text-sm font-medium text-ink-200">
              {streamingMetrics.avg_tps?.toFixed(1)} tok/s
            </div>
            <div className="text-xs text-ink-400">Avg TPS</div>
          </div>
          <div>
            <div className="text-sm font-medium text-ink-200">
              {formatPercent(streamingMetrics.avg_continuity)}
            </div>
            <div className="text-xs text-ink-400">Continuity</div>
          </div>
          <div>
            <div className="text-sm font-medium text-ink-200">
              {costMetrics.token_savings_pct?.toFixed(1)}%
            </div>
            <div className="text-xs text-ink-400">Token Savings</div>
          </div>
        </div>
      )}
    </CardContent>
  </Card>
)}
```

### FR-7: Backend Composite Score Calculation

Add endpoint for composite score:

```python
# backend/app/api/janus.py

from fastapi import APIRouter

router = APIRouter(prefix="/api/janus", tags=["janus"])

@router.get("/composite-score/{run_id}")
async def get_composite_score(run_id: str) -> dict:
    """
    Calculate Janus composite score for a run.

    Returns breakdown by category and overall composite.
    """
    from app.benchmarks.janus_scoring import calculate_janus_composite_score

    run = await get_run(run_id)
    benchmark_results = {}

    for rb in run.benchmarks:
        if rb.benchmark_name.startswith("janus_"):
            benchmark_results[rb.benchmark_name] = {
                "score": rb.score,
                "metrics": rb.metrics or {}
            }

    return calculate_janus_composite_score(benchmark_results)
```

### FR-8: Janus Provider Option

Add Janus as a provider option:

```tsx
// In provider selection

<SelectItem value="janus">Janus Gateway</SelectItem>
```

This allows testing implementations via the Janus gateway URL.

## Non-Functional Requirements

### NFR-1: Visual Consistency

- Janus section uses moss green accent color
- Follows existing card and layout patterns
- Responsive on mobile

### NFR-2: Performance

- Category sorting is memoized
- Composite score calculation is cached
- UI updates smoothly during runs

### NFR-3: Accessibility

- All new elements have proper labels
- Color coding has text alternatives
- Keyboard navigation works

## Acceptance Criteria

- [ ] "Janus Intelligence" category appears in benchmark list
- [ ] All 5 Janus benchmarks display correctly
- [ ] "Select All Janus" button works
- [ ] Composite score weights displayed
- [ ] Run results show Janus composite score
- [ ] Streaming metrics (TTFT, TPS) displayed
- [ ] Cost metrics displayed
- [ ] Janus provider option available
- [ ] Mobile responsive
- [ ] Tests pass

## Files to Modify

```
chutes-bench-runner/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── benchmarks.py    # MODIFY - include category in response
│   │   │   └── janus.py         # NEW - composite score endpoint
│   │   └── benchmarks/
│   │       └── janus_scoring.py # NEW - scoring calculation
│
└── frontend/
    ├── components/
    │   └── benchmark-runner.tsx # MODIFY - add Janus category UI
    ├── lib/
    │   └── api.ts               # MODIFY - add types and endpoints
    └── app/
        └── runs/
            └── [id]/
                └── page.tsx     # MODIFY - add composite score display
```

## Visual Reference

### Benchmark Selection UI

```
┌─────────────────────────────────────────────────────────────┐
│  JANUS INTELLIGENCE                            5 benchmarks │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Janus Competition Benchmarks              [Select All]  │ │
│ │ These benchmarks measure research, tool use, multimodal,│ │
│ │ streaming, and cost efficiency.                         │ │
│ │                                                         │ │
│ │ Quality  Speed   Cost    Streaming  Modality            │ │
│ │   40%     20%    15%       15%        10%               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────┐ │
│ │☑ Janus Research  │ │☑ Janus Tool Use  │ │☑ Janus Multi │ │
│ │  100 tests       │ │  80 tests        │ │  60 tests    │ │
│ │  Est. ~15 min    │ │  Est. ~10 min    │ │  Est. ~20 min│ │
│ └──────────────────┘ └──────────────────┘ └──────────────┘ │
│ ┌──────────────────┐ ┌──────────────────┐                   │
│ │☑ Janus Streaming │ │☑ Janus Cost      │                   │
│ │  50 tests        │ │  40 tests        │                   │
│ │  Est. ~8 min     │ │  Est. ~5 min     │                   │
│ └──────────────────┘ └──────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Results Display

```
┌─────────────────────────────────────────────────────────────┐
│ Janus Composite Score                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    78.5%     82.1%    75.2%    71.0%    80.5%    73.0%     │
│  COMPOSITE  Quality   Speed    Cost   Streaming Modality   │
│             (40%)    (20%)   (15%)    (15%)     (10%)      │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 450ms avg TTFT  │  25.3 tok/s  │  76% continuity  │ 12% │ │
│ │                 │     TPS      │                  │saved│ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Open Questions / Risks

1. **Category ordering**: Should Janus be above or below Core Benchmarks?
2. **Default selection**: Should Janus benchmarks be selected by default?
3. **Provider URL**: What is the Janus gateway URL for testing?
4. **Backward compatibility**: Do existing runs need migration?

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Overview and scoring weights
- `specs/competition/02_description_and_scoring.md` - Leaderboard display
- `specs/34_janus_streaming_benchmark.md` - Streaming metrics
