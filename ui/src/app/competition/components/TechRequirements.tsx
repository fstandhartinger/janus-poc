const apiEndpoints = [
  { endpoint: '/v1/chat/completions', method: 'POST', required: 'Yes' },
  { endpoint: '/health', method: 'GET', required: 'Yes' },
  { endpoint: '/v1/models', method: 'GET', required: 'No (recommended)' },
];

const streamingRequirements = [
  'Must support stream: true for SSE responses.',
  'Continuous output: tokens should flow continuously, not in batches.',
  'Reasoning tokens: use reasoning_content for thinking/planning.',
  'Finish reason: always include finish_reason in the final chunk.',
];

const resourceLimits = [
  { resource: 'Memory', limit: '16 GB' },
  { resource: 'CPU', limit: '4 cores' },
  { resource: 'Disk', limit: '50 GB' },
  { resource: 'Network', limit: 'Whitelisted egress only' },
  { resource: 'Timeout', limit: '5 minutes per request' },
];

const egressEndpoints = [
  'api.chutes.ai',
  'proxy.janus.rodeo',
  'search.janus.rodeo',
  'sandbox.janus.rodeo',
  'vector.janus.rodeo',
];

export function TechRequirements() {
  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        <div className="text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
            Requirements
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Technical Requirements
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Validate your container against the required API contract, streaming
            behavior, and resource limits before you submit.
          </p>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              API endpoints
            </p>
            <table className="w-full text-left text-sm mt-4">
              <thead>
                <tr className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">
                  <th className="pb-2">Endpoint</th>
                  <th className="pb-2">Method</th>
                  <th className="pb-2">Required</th>
                </tr>
              </thead>
              <tbody>
                {apiEndpoints.map((endpoint) => (
                  <tr key={endpoint.endpoint} className="border-t border-[#1F2937]">
                    <td className="py-2 text-[#F3F4F6]">{endpoint.endpoint}</td>
                    <td className="py-2 text-[#D1D5DB]">{endpoint.method}</td>
                    <td className="py-2 text-[#9CA3AF]">{endpoint.required}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="glass-card p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Streaming requirements
            </p>
            <ul className="mt-4 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
              {streamingRequirements.map((requirement) => (
                <li key={requirement}>{requirement}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="glass-card p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Resource limits
            </p>
            <table className="w-full text-left text-sm mt-4">
              <thead>
                <tr className="text-xs uppercase tracking-[0.2em] text-[#6B7280]">
                  <th className="pb-2">Resource</th>
                  <th className="pb-2">Limit</th>
                </tr>
              </thead>
              <tbody>
                {resourceLimits.map((limit) => (
                  <tr key={limit.resource} className="border-t border-[#1F2937]">
                    <td className="py-2 text-[#F3F4F6]">{limit.resource}</td>
                    <td className="py-2 text-[#9CA3AF]">{limit.limit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="glass-card p-6">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Whitelisted egress
            </p>
            <p className="text-sm text-[#9CA3AF] mt-3">
              Only these services are reachable from the container. All other outbound
              traffic is blocked.
            </p>
            <ul className="mt-4 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
              {egressEndpoints.map((endpoint) => (
                <li key={endpoint}>{endpoint}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
