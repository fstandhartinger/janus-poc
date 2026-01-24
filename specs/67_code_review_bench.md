# Spec 67: Code Review - Benchmark Runner (janus-bench)

## Status: DRAFT

## Context / Why

The benchmark runner (janus-bench) is responsible for evaluating competitors against the Janus benchmark suite. It includes benchmark adapters, scoring logic, and result collection. A thorough code review is needed to identify and fix:

- Bugs and edge cases
- Performance bottlenecks
- Design/architecture issues
- Naming inconsistencies
- Overly complicated solutions
- Scoring accuracy issues
- Error handling gaps
- Logging deficiencies

## Scope

Review all code in `bench/`:

```
bench/
├── janus_bench/
│   ├── __init__.py
│   ├── config.py                  # Settings
│   ├── main.py                    # CLI entry point
│   ├── runner.py                  # Benchmark execution
│   ├── scoring.py                 # Score calculation
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                # Base adapter
│   │   ├── research.py            # janus_research
│   │   ├── tool_use.py            # janus_tool_use
│   │   ├── multimodal.py          # janus_multimodal
│   │   ├── streaming.py           # janus_streaming
│   │   └── cost.py                # janus_cost
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── quality.py             # Quality metrics
│   │   ├── latency.py             # Latency metrics
│   │   └── cost.py                # Cost metrics
│   └── reports/
│       ├── __init__.py
│       └── generator.py           # Report generation
└── tests/
```

## Review Checklist

### 1. Configuration (config.py)

- [ ] **Settings**: All settings configurable
- [ ] **Validation**: Types validated
- [ ] **Defaults**: Sensible defaults
- [ ] **Sampling**: Subset sampling works
- [ ] **Seed**: Deterministic with seed

### 2. Runner (runner.py)

- [ ] **Task execution**: Tasks run correctly
- [ ] **Concurrency**: Parallel execution if used
- [ ] **Timeout**: Task timeout enforced
- [ ] **Progress**: Progress updates streamed
- [ ] **Error handling**: Task failures handled
- [ ] **Resource cleanup**: Cleanup on completion

### 3. Adapters (adapters/*.py)

#### Base Adapter
- [ ] **Interface**: Clear abstract interface
- [ ] **Task loading**: Items loaded correctly
- [ ] **Scoring**: Score method defined
- [ ] **Cleanup**: Resources cleaned

#### Research Adapter
- [ ] **100 items**: Full task set
- [ ] **Web search**: Tasks test search
- [ ] **Fact verification**: Accuracy checked
- [ ] **Scoring**: Quality metrics used

#### Tool Use Adapter
- [ ] **80 items**: Full task set
- [ ] **Function calling**: Tool use tested
- [ ] **API integration**: External APIs tested
- [ ] **Scoring**: Correctness checked

#### Multimodal Adapter
- [ ] **60 items**: Full task set
- [ ] **Image tasks**: Vision tested
- [ ] **Audio tasks**: Speech tested
- [ ] **Video tasks**: Video tested
- [ ] **Scoring**: Quality metrics

#### Streaming Adapter
- [ ] **50 items**: Full task set
- [ ] **TTFT**: Time to first token measured
- [ ] **TPS**: Tokens per second calculated
- [ ] **Continuity**: Gap detection
- [ ] **Keep-alives**: Frequency checked

#### Cost Adapter
- [ ] **40 items**: Full task set
- [ ] **Token counting**: Accurate count
- [ ] **Cost calculation**: Correct formula
- [ ] **Efficiency**: Quality/cost ratio

### 4. Metrics (metrics/*.py)

- [ ] **Quality metrics**: Accuracy, relevance
- [ ] **Latency metrics**: TTFT, TPS, gaps
- [ ] **Cost metrics**: Tokens, cost
- [ ] **Aggregation**: Averages, percentiles
- [ ] **Normalization**: 0-1 scale

### 5. Scoring (scoring.py)

- [ ] **Composite formula**: 40% quality + 20% speed + 15% cost + 15% streaming + 10% modality
- [ ] **Category scores**: Individual scores correct
- [ ] **Normalization**: 0-1 scale
- [ ] **Reproducibility**: Same seed = same score
- [ ] **Edge cases**: Zero scores, missing data

### 6. Reports (reports/generator.py)

- [ ] **Format**: Report structure clear
- [ ] **Completeness**: All metrics included
- [ ] **Readability**: Human-readable output
- [ ] **Export**: JSON/CSV export if needed

### 7. CLI (main.py)

- [ ] **Arguments**: CLI args parsed
- [ ] **Subcommands**: Commands organized
- [ ] **Help text**: Usage documented
- [ ] **Exit codes**: Proper exit codes

### 8. General Code Quality

- [ ] **DRY**: No duplication
- [ ] **Complexity**: Functions not too long
- [ ] **Type hints**: Complete
- [ ] **Docstrings**: Public functions documented
- [ ] **Async**: Proper async patterns
- [ ] **Tests**: Good coverage

## Common Issues to Look For

### Scoring Accuracy
- Metrics calculated incorrectly
- Normalization errors
- Edge cases not handled
- Reproducibility issues

### Performance
- Sequential when could be parallel
- Large datasets in memory
- Slow metric calculations
- Unnecessary API calls

### Reliability
- Task failures crash runner
- Timeout not enforced
- Resource leaks
- State corruption

### Maintainability
- Hard to add new adapters
- Magic numbers
- Unclear scoring logic
- Poor test coverage

## Improvement Actions

For each issue found:

1. **Document**: File, line, issue
2. **Categorize**: Bug, Performance, Scoring, Design, Naming
3. **Prioritize**: Critical, High, Medium, Low
4. **Fix**: Implement fix
5. **Test**: Add/update tests
6. **Validate**: Run against baseline

## Deliverables

- [ ] All issues fixed
- [ ] Scoring verified accurate
- [ ] Tests updated
- [ ] No regression
- [ ] Documentation current

## Acceptance Criteria

- [ ] Zero linting errors
- [ ] All tests pass
- [ ] Scoring reproducible
- [ ] All adapters work
- [ ] Reports generated correctly
- [ ] Performance acceptable
