export function SubmissionSection() {
  const requirements = [
    'Component manifest (JSON)',
    'API contract (OpenAPI or MCP tool schema)',
    'Documentation and examples',
    'Docker container or hosted endpoint',
    'License (open source preferred)',
  ];

  return (
    <section className="py-16 lg:py-24" id="submit">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-8 lg:p-10">
          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Submit your component
              </p>
              <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
                Share Your Building Blocks
              </h2>
              <p className="text-[#9CA3AF]">
                The submission workflow is launching in Phase 2. Meanwhile, we are
                collecting the best component ideas and early interest.
              </p>
              <button
                type="button"
                className="btn-secondary text-base px-8 py-3 cursor-not-allowed opacity-60"
                disabled
              >
                Coming Soon
              </button>
            </div>
            <div className="bg-[#0B0F14] border border-[#1F2937] rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-[#F3F4F6]">
                Submission Requirements
              </h3>
              <ul className="mt-4 space-y-3 text-sm text-[#9CA3AF] list-disc list-inside">
                {requirements.map((requirement) => (
                  <li key={requirement}>{requirement}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
