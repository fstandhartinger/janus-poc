export function SubmissionForm() {
  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-8">
          <div className="space-y-4">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Submission form
            </p>
            <h2 className="text-3xl font-semibold text-[#F3F4F6]">
              Submit Your Implementation for Review
            </h2>
            <p className="text-[#9CA3AF]">
              This is a placeholder form for the PoC. Submissions are manually
              reviewed before running on private benchmarks.
            </p>
          </div>

          <form className="mt-8 grid md:grid-cols-2 gap-6">
            <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
              Competitor Name
              <input
                type="text"
                placeholder="baseline-v2"
                className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
              Contact Email
              <input
                type="email"
                placeholder="team@rodeo.dev"
                className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
              Container Image URL
              <input
                type="text"
                placeholder="docker.io/user/janus-engine:v1"
                className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
              />
            </label>
            <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
              Brief Description
              <textarea
                rows={4}
                placeholder="What makes your implementation unique?"
                className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
              />
            </label>
            <label className="flex items-start gap-3 text-sm text-[#D1D5DB] md:col-span-2">
              <input
                type="checkbox"
                className="mt-1 accent-[#63D297]"
              />
              I agree to the competition rules and confirm my submission meets the
              security requirements.
            </label>
            <div className="md:col-span-2 flex flex-col sm:flex-row gap-3 items-start">
              <button type="button" className="btn-primary px-6 py-3">
                Submit for Review
              </button>
              <span className="text-xs text-[#6B7280]">
                Submissions are manually reviewed. Expect a response within 72
                hours.
              </span>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}
