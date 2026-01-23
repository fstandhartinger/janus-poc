import { MermaidDiagram } from '@/components/MermaidDiagram';

const improvementChart = `flowchart LR
    A[Current #1] -->|Fork and improve| B[Your Submission]
    B -->|If better| C[New #1]
    C -->|Others fork| D[Next Improvement]
    D --> C`;

const licenseRows = [
  { license: 'MIT', allowed: 'Yes', notes: 'Recommended' },
  { license: 'Apache 2.0', allowed: 'Yes', notes: 'Recommended' },
  { license: 'GPL v3', allowed: 'Yes', notes: 'Derivative works must also be GPL' },
  { license: 'BSD 3-Clause', allowed: 'Yes', notes: '' },
  { license: 'AGPL v3', allowed: 'Yes', notes: 'Network use triggers copyleft' },
  { license: 'Proprietary', allowed: 'No', notes: 'Not allowed' },
  { license: 'No license', allowed: 'No', notes: 'Defaults to proprietary' },
];

const reviewChecklist = [
  'Docker image accessible from the specified registry.',
  'API compliance for /v1/chat/completions and /health.',
  'Source code repository is public and matches the image.',
  'License file is OSI-approved.',
  'No obvious malicious code or data exfiltration.',
  'No unapproved egress beyond whitelisted services.',
  'Hotkey is valid and registered on Bittensor.',
  'Dockerfile can reproduce the image from source.',
];

const reviewTimeline = [
  'Submission received - review begins within 24 hours.',
  'Review complete - benchmarks run within 48 hours.',
  'Results published - leaderboard updated within 72 hours.',
];

const decentralizedSteps = [
  'Validator set of trusted community reviewers.',
  'Randomized assignment of submissions to reviewers.',
  'Consensus approval required to pass.',
  'Slashing for malicious or negligent reviewers.',
  'Appeals handled by the broader panel.',
];

export function SubmissionGuide() {
  return (
    <section id="submission-guide" className="py-16 lg:py-24 bg-[#111726]/40">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
            Submission requirements
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            What It Means to Submit to Janus
          </h2>
          <p className="text-[#9CA3AF] mt-4 max-w-3xl mx-auto">
            Your submission is an open source Docker implementation that speaks the
            OpenAI Chat Completions API. The competition rewards incremental progress,
            transparency, and reproducibility.
          </p>
        </div>

        <div className="space-y-8">
          <div className="glass-card p-6 grid lg:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                What You&apos;re Submitting
              </h3>
              <p className="text-sm text-[#9CA3AF]">
                A Janus submission is a Docker container that implements an
                OpenAI-compatible Chat Completions API. Behind that API, your
                implementation can use any technology to generate responses.
              </p>
              <ul className="space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                <li>It is not &quot;an agent&quot; - it is an implementation of intelligence.</li>
                <li>It is not &quot;a miner&quot; - the miner is you; the submission is your creation.</li>
                <li>It is a Docker container - portable, reproducible, isolated.</li>
                <li>It exposes a standard API - POST /v1/chat/completions, GET /health.</li>
              </ul>
            </div>
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                What Happens to Your Submission
              </h3>
              <ol className="space-y-3 text-sm text-[#D1D5DB] list-decimal list-inside">
                <li>Your container is pulled and deployed to a Chutes CPU TEE node.</li>
                <li>It connects to platform services: web proxy, search, sandbox, inference.</li>
                <li>Benchmarks run against it via the same API users call.</li>
                <li>Results are published to the leaderboard.</li>
              </ol>
            </div>
          </div>

          <div className="glass-card p-6 grid lg:grid-cols-[1.1fr_0.9fr] gap-6">
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">Build on What Exists</h3>
              <p className="text-sm text-[#9CA3AF]">
                The competition encourages incremental improvement. Start from the
                current leader, make it better, and push the frontier forward.
              </p>
              <div className="space-y-3">
                <p className="text-sm text-[#F3F4F6] font-semibold">Why incremental?</p>
                <ul className="space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  <li>Lower barrier: improve a slice instead of rebuilding everything.</li>
                  <li>Faster progress: small improvements compound into big gains.</li>
                  <li>Community learning: each submission teaches the next.</li>
                  <li>Reduced risk: if your change fails, the delta is small.</li>
                </ul>
              </div>
              <div className="space-y-3">
                <p className="text-sm text-[#F3F4F6] font-semibold">How to start</p>
                <ol className="space-y-2 text-sm text-[#D1D5DB] list-decimal list-inside">
                  <li>Fork the baseline: git clone https://github.com/chutesai/janus-baseline</li>
                  <li>Study the leader: review the current #1 source code.</li>
                  <li>Identify a weakness: use benchmark breakdowns to find gaps.</li>
                  <li>Make your improvement: prompts, routing, new capabilities.</li>
                  <li>Test locally: run janus-bench to validate.</li>
                  <li>Submit your enhanced version.</li>
                </ol>
              </div>
            </div>
            <div className="bg-[#0B0F14] border border-[#1F2937] rounded-2xl p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280] mb-3">
                Improvement cycle
              </p>
              <MermaidDiagram chart={improvementChart} ariaLabel="Incremental improvement cycle" />
            </div>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                Open Source Requirement
              </h3>
              <p className="text-sm text-[#9CA3AF]">
                All Janus submissions must be open source. This is non-negotiable.
              </p>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Rationale</p>
                <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  <li>Community progress: everyone learns and improves faster.</li>
                  <li>Transparency: users can inspect how requests are handled.</li>
                  <li>Security: open code can be audited.</li>
                  <li>Bittensor ethos: the network is built on openness.</li>
                </ul>
              </div>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Acceptable licenses</p>
                <div className="mt-3 overflow-hidden border border-[#1F2937] rounded-xl">
                  <table className="w-full text-sm text-left text-[#D1D5DB]">
                    <thead className="bg-[#0B111A] text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                      <tr>
                        <th className="px-3 py-2">License</th>
                        <th className="px-3 py-2">Allowed</th>
                        <th className="px-3 py-2">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {licenseRows.map((row) => (
                        <tr key={row.license} className="border-t border-[#1F2937]">
                          <td className="px-3 py-2">{row.license}</td>
                          <td className="px-3 py-2">{row.allowed}</td>
                          <td className="px-3 py-2 text-[#9CA3AF]">{row.notes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-[#F3F4F6] font-semibold">What must be open</p>
                  <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                    <li>Source code that runs inside the container.</li>
                    <li>Prompts, few-shot examples, templates.</li>
                    <li>Configuration and routing rules.</li>
                    <li>Dependency lists and Dockerfiles.</li>
                  </ul>
                </div>
                <div>
                  <p className="text-sm text-[#F3F4F6] font-semibold">What can stay private</p>
                  <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                    <li>API keys stored in environment variables.</li>
                    <li>Training data for fine-tuned models.</li>
                    <li>Calls to proprietary models or APIs.</li>
                  </ul>
                </div>
              </div>
            </div>

            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                Bittensor Hotkey Requirement
              </h3>
              <p className="text-sm text-[#9CA3AF]">
                Every submission must include the miner&apos;s Bittensor hotkey (SS58
                address) for attribution and payouts.
              </p>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Why hotkey?</p>
                <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  <li>Attribution on the leaderboard.</li>
                  <li>Prize pool payouts to the linked coldkey.</li>
                  <li>Reputation history across submissions.</li>
                  <li>Future Subnet 64 integration.</li>
                </ul>
              </div>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Hotkey format</p>
                <p className="mt-2 text-sm text-[#D1D5DB]">
                  SS58 address format (starts with 5). Example:
                </p>
                <p className="mt-2 text-xs font-mono text-[#63D297]">
                  5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty
                </p>
              </div>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Validation</p>
                <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  <li>Hotkey format is validated on submission.</li>
                  <li>Hotkey must be registered on Bittensor (phase dependent).</li>
                  <li>One hotkey can submit multiple versions.</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="glass-card p-6 grid lg:grid-cols-[1.1fr_0.9fr] gap-6">
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">Review Process</h3>
              <p className="text-sm text-[#9CA3AF]">
                Current Phase: manual review before a submission appears on the
                leaderboard.
              </p>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Review checklist</p>
                <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  {reviewChecklist.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <p className="text-sm text-[#F3F4F6] font-semibold">Timeline</p>
                <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                  {reviewTimeline.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                Future Phase: Decentralized Review
              </h3>
              <p className="text-sm text-[#9CA3AF]">
                Phase 2 introduces a decentralized judging panel with consensus-based
                approvals and staking-backed incentives.
              </p>
              <ul className="space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
                {decentralizedSteps.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="text-xs text-[#6B7280]">
                This phase will be specified separately once governance is finalized.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
