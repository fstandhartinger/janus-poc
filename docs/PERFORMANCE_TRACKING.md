# Baseline Performance Tracking

## Current Scores

| Date | Baseline | Composite | Quality | Speed | Cost | Streaming | Multimodal |
|------|----------|-----------|---------|-------|------|-----------|------------|
| 2026-01-25 | CLI | 46.68 | 43.49 | 90.90 | 60.62 | 3.95 | 14.17 |
| 2026-01-25 | LangChain | 46.48 | 40.60 | 95.22 | 63.11 | 3.19 | 12.50 |

## Improvement History

### 2026-01-24: Streaming Optimization
- **Change**: Added chunk batching and cadence smoothing for SSE responses.
- **Impact**: Streaming smoke test now passes with TTFT ~1s and >250 chunks on both baselines.
- **Files**: `baseline-agent-cli/janus_baseline_agent_cli/streaming.py`, `baseline-agent-cli/janus_baseline_agent_cli/main.py`, `baseline-langchain/janus_baseline_langchain/streaming.py`, `baseline-langchain/janus_baseline_langchain/main.py`

### 2026-01-24: Tool Parsing Robustness
- **Change**: Added defensive tool argument parsing.
- **Impact**: Tool-call smoke tests pass; benchmark tool-use still underperforms and remains a focus area.
- **Files**: `baseline-agent-cli/janus_baseline_agent_cli/tools/parser.py`, `baseline-langchain/janus_baseline_langchain/tools/robust.py`

### 2026-01-24: Prompt/Context Efficiency
- **Change**: Added prompt and context optimization helpers.
- **Impact**: Reduced average latency in smoke tests; applied in fast path to limit unnecessary tokens.
- **Files**: `baseline-agent-cli/janus_baseline_agent_cli/agent/efficiency.py`, `baseline-agent-cli/janus_baseline_agent_cli/services/llm.py`

### 2026-01-25: Model & Vision Tuning
- **Change**: Switched primary model to `NousResearch/Hermes-4-14B` and vision routing to `Qwen/Qwen2.5-VL-32B-Instruct`.
- **Impact**: Composite score improved from ~23.25 to ~46.5 (+100%); full benchmark suite completed for both baselines.
- **Files**: Runtime env (`BASELINE_AGENT_CLI_MODEL`, `BASELINE_LANGCHAIN_MODEL`, vision model overrides)

## Learnings for Competitors

- Prefer models that support tool calling; otherwise tool-use benchmarks degrade sharply.
- Strip `null` fields from SSE deltas to avoid downstream parser errors (especially around `tool_calls`).
- Vision model choice has an outsized impact on multimodal latency; smaller VL models reduce tail latency.
- Chunking large streaming deltas improves streaming scores without changing model output semantics.

## Known Issues

1. Tool-use benchmark success rates remain low (especially chained/tool-selection tasks).
2. Streaming continuity gaps are high despite improved TTFT.
3. Some multimodal generation tasks still spike latency (monitor image generation throughput).

## Next Priorities

1. Improve tool-call reliability (especially multi-step tool chains) and re-run tool-use benchmarks.
2. Reduce continuity gaps by adjusting chunk cadence and buffer thresholds.
3. Track image-generation latency spikes and add retry/backoff where needed.
