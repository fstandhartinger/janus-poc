const useCaseCategories = [
  {
    title: 'Simple chat',
    description: 'Conversational responses, Q&A, summarization.',
  },
  {
    title: 'Complex reasoning',
    description: 'Multi-step problems, logical deduction, planning.',
  },
  {
    title: 'Deep research',
    description: 'Web search, information synthesis, citation.',
  },
  {
    title: 'Software creation',
    description: 'Code generation, debugging, full project scaffolding.',
  },
  {
    title: 'Multimodal input',
    description: 'Understanding images, documents, audio.',
  },
  {
    title: 'Multimodal output',
    description: 'Generating images, files, structured data.',
  },
  {
    title: 'Tool use',
    description: 'Calling APIs, executing code, managing files.',
  },
];

const nonFunctionalMetrics = [
  {
    title: 'Quality',
    description: 'Accuracy, helpfulness, safety, instruction following.',
  },
  {
    title: 'Speed',
    description: 'Time to first token, total completion time.',
  },
  {
    title: 'Cost',
    description: 'Resource efficiency, inference cost per request.',
  },
  {
    title: 'Streaming continuity',
    description: 'Consistent token flow, reasoning transparency.',
  },
  {
    title: 'Modality handling',
    description: 'Graceful handling of images, files, multi-turn context.',
  },
];

export function CompetitionOverview() {
  return (
    <section className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Competition overview
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              What is the Janus Competition?
            </h2>
            <p className="text-[#9CA3AF]">
              The Janus Competition is an open arena where developers compete to build
              the best intelligence engine - a system that handles any request a user
              might throw at a comprehensive AI assistant.
            </p>

            <div className="space-y-3">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">How It Works</h3>
              <p className="text-[#9CA3AF]">
                You submit an OpenAI-compatible API endpoint. Behind that endpoint, your
                implementation can use any technology: CLI agents, workflow engines,
                model routers, multi-agent orchestrations, or entirely novel approaches.
                As long as it speaks the OpenAI Chat Completions API and streams
                responses, you&apos;re in.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">What Gets Evaluated</h3>
              <p className="text-[#9CA3AF]">
                Your implementation is scored across all the use cases of a modern AI
                assistant and the production metrics that define a great experience.
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass-card p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                Use case coverage
              </p>
              <ul className="mt-4 space-y-3 text-sm text-[#9CA3AF]">
                {useCaseCategories.map((category) => (
                  <li key={category.title}>
                    <span className="text-[#F3F4F6] font-semibold">{category.title}:</span>{' '}
                    {category.description}
                  </li>
                ))}
              </ul>
            </div>

            <div className="glass-card p-6">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                Non-functional metrics
              </p>
              <ul className="mt-4 space-y-3 text-sm text-[#9CA3AF]">
                {nonFunctionalMetrics.map((metric) => (
                  <li key={metric.title}>
                    <span className="text-[#F3F4F6] font-semibold">{metric.title}:</span>{' '}
                    {metric.description}
                  </li>
                ))}
              </ul>
            </div>

            <p className="text-sm text-[#9CA3AF]">
              The composite score reflects how well your implementation performs as a
              complete AI solution, not just on narrow benchmarks.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
