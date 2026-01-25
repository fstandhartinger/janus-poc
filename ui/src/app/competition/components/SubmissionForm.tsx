export function SubmissionForm() {
  return (
    <section id="submission-portal" className="py-16 lg:py-24">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-8 lg:p-10">
          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Submission form
              </p>
              <h2 className="text-3xl font-semibold text-[#F3F4F6]">
                Submit Your Implementation for Review
              </h2>
              <p className="text-[#9CA3AF]">
                Submissions are manually reviewed before running on private benchmarks.
                Use this form to share your Docker image, hotkey, source code, and
                license details.
              </p>

              <div className="mt-6">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">
                  Submission fields
                </p>
                <div className="overflow-hidden border border-[#1F2937] rounded-xl">
                  <table className="w-full text-sm text-left text-[#D1D5DB]">
                    <thead className="bg-[#0B111A] text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                      <tr>
                        <th className="px-3 py-2">Field</th>
                        <th className="px-3 py-2">Required</th>
                        <th className="px-3 py-2">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Implementation Name</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          Unique identifier (e.g., &quot;turbo-reasoner-v2&quot;)
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Docker Image</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          Full image reference (e.g., ghcr.io/user/janus-impl:v2)
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Bittensor Hotkey</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          SS58 address for attribution and payout
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Source Code URL</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          Link to public repository (GitHub, GitLab, etc.)
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">License</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          OSI-approved license identifier (e.g., &quot;MIT&quot;)
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Description</td>
                        <td className="px-3 py-2">Yes</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          Brief description of your approach (100-500 chars)
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Changelog</td>
                        <td className="px-3 py-2">No</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          What differs from baseline or previous version
                        </td>
                      </tr>
                      <tr className="border-t border-[#1F2937]">
                        <td className="px-3 py-2">Contact</td>
                        <td className="px-3 py-2">No</td>
                        <td className="px-3 py-2 text-[#9CA3AF]">
                          Discord handle or email for review communication
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="mt-6">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">
                  Example submission
                </p>
                <pre className="bg-[#0B111A] border border-[#1F2937] rounded-xl p-4 text-xs text-[#D1D5DB] whitespace-pre-wrap">
{`name: "turbo-reasoner-v2"
image: "ghcr.io/alice/janus-turbo:2.0.1"
hotkey: "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
source: "https://github.com/alice/janus-turbo"
license: "MIT"
description: "Enhanced reasoning via chain-of-thought decomposition and parallel tool execution. Improves on baseline-v3 with 15% better GSM8K scores."
changelog: "Added CoT decomposition, parallel tool calls, improved code generation prompts"
contact: "alice#1234"`}
                </pre>
              </div>
            </div>

            <form className="grid md:grid-cols-2 gap-4">
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
                Implementation Name
                <input
                  type="text"
                  placeholder="turbo-reasoner-v2"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
                Docker Image
                <input
                  type="text"
                  placeholder="ghcr.io/user/janus-impl:v2"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
                Bittensor Hotkey
                <input
                  type="text"
                  placeholder="5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
                Source Code URL
                <input
                  type="text"
                  placeholder="https://github.com/you/janus-implementation"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
                License
                <input
                  type="text"
                  placeholder="MIT"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB]">
                Contact (optional)
                <input
                  type="text"
                  placeholder="alice#1234 or team@rodeo.dev"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
                Description (100-500 chars)
                <textarea
                  rows={3}
                  placeholder="Briefly describe your approach and improvements."
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex flex-col gap-2 text-sm text-[#D1D5DB] md:col-span-2">
                Changelog (optional)
                <textarea
                  rows={3}
                  placeholder="What changed since the last version or baseline?"
                  className="bg-[#0B111A] border border-[#1F2937] rounded-lg px-3 py-2 text-[#F3F4F6]"
                />
              </label>
              <label className="flex items-start gap-3 text-sm text-[#D1D5DB] md:col-span-2">
                <input type="checkbox" className="mt-1 accent-[#63D297]" />
                I confirm this submission is open source and meets the security
                requirements.
              </label>
              <div className="md:col-span-2 flex flex-col sm:flex-row gap-3 items-start">
                <button type="button" className="btn-primary px-6 py-3">
                  Submit for Review
                </button>
                <span className="text-xs text-[#6B7280]">
                  Submissions are manually reviewed. Expect benchmarks within 48 hours
                  and results within 72 hours.
                </span>
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
