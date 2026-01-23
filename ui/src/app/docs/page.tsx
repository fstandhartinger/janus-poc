import { Header, Footer } from '@/components/landing';

const quickstart = `curl https://janus-gateway-bqou.onrender.com/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline",
    "messages": [{ "role": "user", "content": "Hello Janus" }],
    "stream": true
  }'`;

export default function DocsPage() {
  return (
    <div className="min-h-screen aurora-bg">
      <Header />
      <main className="py-16 lg:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="glass-card p-8 lg:p-10">
            <p className="text-xs uppercase tracking-[0.35em] text-[#9CA3AF]">API Docs</p>
            <h1 className="mt-4 text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Janus OpenAI-compatible endpoints
            </h1>
            <p className="mt-4 text-[#9CA3AF] text-lg leading-relaxed">
              Janus implements the OpenAI Chat Completions contract with streaming responses,
              artifacts, and reasoning content. Use the same request shape you already have.
            </p>

            <div className="mt-8 flex flex-wrap gap-3">
              <span className="px-3 py-1 rounded-full border border-[#1F2937] text-sm text-[#D1D5DB]">
                POST /v1/chat/completions
              </span>
              <span className="px-3 py-1 rounded-full border border-[#1F2937] text-sm text-[#D1D5DB]">
                GET /v1/models
              </span>
              <span className="px-3 py-1 rounded-full border border-[#1F2937] text-sm text-[#D1D5DB]">
                GET /v1/artifacts/:id
              </span>
            </div>

            <div className="mt-8 code-panel">
              <div className="code-panel-header">
                <span>curl</span>
                <span className="text-[#6B7280]">Quickstart</span>
              </div>
              <pre className="code-block">
                <code>{quickstart}</code>
              </pre>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
