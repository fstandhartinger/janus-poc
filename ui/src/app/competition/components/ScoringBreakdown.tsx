const scoringCategories = [
  {
    category: 'Chat Quality',
    measures: 'Conversational ability, helpfulness.',
    benchmarks: 'MT-Bench, AlpacaEval',
  },
  {
    category: 'Reasoning',
    measures: 'Logic, math, multi-step problems.',
    benchmarks: 'GSM8K, MATH, ARC',
  },
  {
    category: 'Knowledge',
    measures: 'Factual accuracy, world knowledge.',
    benchmarks: 'MMLU, TruthfulQA',
  },
  {
    category: 'Research',
    measures: 'Web search, synthesis, citation.',
    benchmarks: 'Custom research tasks',
  },
  {
    category: 'Coding',
    measures: 'Code generation, debugging, explanation.',
    benchmarks: 'HumanEval, MBPP, SWE-Bench',
  },
  {
    category: 'Tool Use',
    measures: 'API calling, function execution.',
    benchmarks: 'Custom tool-use evals',
  },
  {
    category: 'Multimodal',
    measures: 'Image understanding, file generation.',
    benchmarks: 'VQA, document tasks',
  },
  {
    category: 'Speed',
    measures: 'Latency, throughput.',
    benchmarks: 'Time-to-first-token, TPS',
  },
  {
    category: 'Cost',
    measures: 'Resource efficiency.',
    benchmarks: 'USD per 1M tokens (effective)',
  },
  {
    category: 'Streaming',
    measures: 'Continuous output, reasoning tokens.',
    benchmarks: 'Streaming continuity score',
  },
];

const weightDistribution = [
  { category: 'Quality (aggregate)', weight: '40%' },
  { category: 'Speed', weight: '20%' },
  { category: 'Cost', weight: '15%' },
  { category: 'Streaming', weight: '15%' },
  { category: 'Modality', weight: '10%' },
];

const publicBenchmarks = [
  'MMLU (knowledge)',
  'TruthfulQA (accuracy)',
  'GSM8K, MATH (reasoning)',
  'HumanEval, MBPP (coding)',
  'MT-Bench (chat quality)',
];

const proprietaryBenchmarks = [
  'Research synthesis tasks',
  'Multi-step tool use scenarios',
  'Streaming continuity tests',
  'Multimodal generation tasks',
];

export function ScoringBreakdown() {
  return (
    <section id="scoring" className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="space-y-4">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
            Scoring model
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
            Scoring Categories
          </h2>
          <p className="text-[#9CA3AF] max-w-3xl">
            Evaluation spans functional performance and production readiness. Each
            category captures a different slice of what makes an intelligence engine
            useful, fast, and safe in the real world.
          </p>
        </div>

        <div className="glass-card p-6 overflow-x-auto">
          <table className="w-full text-left border-separate border-spacing-y-2">
            <thead>
              <tr className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                <th className="pb-2">Category</th>
                <th className="pb-2">What it measures</th>
                <th className="pb-2">Example benchmarks</th>
              </tr>
            </thead>
            <tbody>
              {scoringCategories.map((category) => (
                <tr key={category.category} className="bg-[#0F172A]/40 rounded-lg">
                  <td className="py-3 px-3 font-semibold text-[#F3F4F6]">
                    {category.category}
                  </td>
                  <td className="py-3 px-3 text-[#D1D5DB]">{category.measures}</td>
                  <td className="py-3 px-3 text-[#9CA3AF]">{category.benchmarks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="space-y-4">
              <h3 className="text-2xl font-semibold text-[#F3F4F6]">Composite Score</h3>
              <p className="text-[#9CA3AF]">
                The final leaderboard ranking is based on a composite score that
                combines all evaluation categories. The formula rewards implementations
                that excel across the board, not just in one area.
              </p>
              <div className="glass p-4 rounded-2xl font-mono text-sm text-[#D1D5DB]">
                CompositeScore = Σ (CategoryScore × CategoryWeight)
              </div>
              <ul className="text-sm text-[#9CA3AF] space-y-2">
                <li>Each category is scored on a normalized scale (0-100).</li>
                <li>Weights reflect real-world usage and are published before each cycle.</li>
                <li>Weights may be adjusted as the competition evolves.</li>
              </ul>
            </div>

            <div className="glass-card p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                Current weight distribution (subject to change)
              </p>
              <table className="w-full text-left mt-4 text-sm">
                <thead>
                  <tr className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">
                    <th className="pb-2">Category</th>
                    <th className="pb-2">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {weightDistribution.map((weight) => (
                    <tr key={weight.category}>
                      <td className="py-2 text-[#D1D5DB]">{weight.category}</td>
                      <td className="py-2 text-[#F3F4F6] font-semibold">{weight.weight}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-xs text-[#6B7280] mt-3">
                Quality aggregate includes chat, reasoning, knowledge, research, coding,
                tool use, and multimodal task performance.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <h3 className="text-2xl font-semibold text-[#F3F4F6]">Benchmark Suites</h3>
              <p className="text-[#9CA3AF]">
                Evaluations use a combination of public and proprietary benchmarks.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 gap-4">
              <div className="glass-card p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                  Public benchmarks
                </p>
                <ul className="mt-3 space-y-2 text-sm text-[#D1D5DB]">
                  {publicBenchmarks.map((benchmark) => (
                    <li key={benchmark}>{benchmark}</li>
                  ))}
                </ul>
              </div>
              <div className="glass-card p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                  Proprietary benchmarks
                </p>
                <ul className="mt-3 space-y-2 text-sm text-[#D1D5DB]">
                  {proprietaryBenchmarks.map((benchmark) => (
                    <li key={benchmark}>{benchmark}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="glass p-4 rounded-2xl text-sm text-[#9CA3AF] space-y-2">
              <p>
                All public benchmark implementations are open source. Proprietary
                benchmarks rotate to prevent overfitting.
              </p>
              <p>
                Scoring runs are reproducible. Questions or disputes can be raised
                through the competition issue tracker, and we will rerun and publish
                findings.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
