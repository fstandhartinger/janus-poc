'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { applyPreReleaseHeader } from '@/lib/preRelease';

type TargetType = 'url' | 'container';
type Suite = 'quick' | 'full' | 'research' | 'tool_use' | 'multimodal' | 'streaming' | 'cost';

const SUITES: { value: Suite; label: string; description: string; duration: string }[] = [
  { value: 'quick', label: 'Quick Suite', description: 'Fast validation with core tests', duration: '~5 min' },
  { value: 'full', label: 'Full Suite', description: 'Complete evaluation across all benchmarks', duration: '~2 hrs' },
  { value: 'research', label: 'Research Only', description: 'Web search and synthesis tasks', duration: '~15 min' },
  { value: 'tool_use', label: 'Tool Use Only', description: 'Function calling and API integration', duration: '~10 min' },
  { value: 'multimodal', label: 'Multimodal Only', description: 'Image generation and vision tasks', duration: '~20 min' },
  { value: 'streaming', label: 'Streaming Only', description: 'TTFT, TPS, continuity metrics', duration: '~8 min' },
  { value: 'cost', label: 'Cost Only', description: 'Token efficiency evaluation', duration: '~5 min' },
];

export function RunSubmitForm() {
  const router = useRouter();
  const [targetType, setTargetType] = useState<TargetType>('url');
  const [targetUrl, setTargetUrl] = useState('');
  const [containerImage, setContainerImage] = useState('');
  const [suite, setSuite] = useState<Suite>('quick');
  const [model, setModel] = useState('deepseek-reasoner');
  const [customModel, setCustomModel] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const modelValue = model === 'custom' && customModel ? customModel : model;
      const response = await fetch('/api/scoring/runs', {
        method: 'POST',
        headers: applyPreReleaseHeader({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          target_type: targetType,
          target_url: targetType === 'url' ? targetUrl : undefined,
          container_image: targetType === 'container' ? containerImage : undefined,
          suite,
          model: modelValue,
          subset_percent: 100,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || 'Failed to create run');
      }

      const run = await response.json();
      router.push(`/competition/scoring/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="submit-run" className="glass-card p-8">
      <h2 className="text-2xl font-semibold text-[#F3F4F6] mb-6">
        Start a Scoring Run
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="space-y-3">
          <label className="text-sm text-[#9CA3AF]">Target Type</label>
          <div className="flex gap-4">
            <button
              type="button"
              onClick={() => setTargetType('url')}
              aria-pressed={targetType === 'url'}
              className={`px-4 py-2 rounded-lg border transition ${
                targetType === 'url'
                  ? 'border-[#63D297] bg-[#63D297]/10 text-[#63D297]'
                  : 'border-white/10 text-[#9CA3AF] hover:border-white/20'
              }`}
            >
              API URL
            </button>
            <button
              type="button"
              onClick={() => setTargetType('container')}
              aria-pressed={targetType === 'container'}
              className={`px-4 py-2 rounded-lg border transition ${
                targetType === 'container'
                  ? 'border-[#63D297] bg-[#63D297]/10 text-[#63D297]'
                  : 'border-white/10 text-[#9CA3AF] hover:border-white/20'
              }`}
            >
              Container Image
            </button>
          </div>
        </div>

        {targetType === 'url' ? (
          <div className="space-y-2">
            <label htmlFor="targetUrl" className="text-sm text-[#9CA3AF]">
              API Endpoint URL
            </label>
            <input
              id="targetUrl"
              type="url"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              placeholder="http://localhost:8080 or https://your-api.example.com"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-[#F3F4F6] placeholder-[#6B7280]
                       focus:outline-none focus:border-[#63D297]/50"
              required
            />
            <p className="text-xs text-[#6B7280]">
              Must expose /v1/chat/completions and /health endpoints
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <label htmlFor="containerImage" className="text-sm text-[#9CA3AF]">
              Container Image
            </label>
            <input
              id="containerImage"
              type="text"
              value={containerImage}
              onChange={(e) => setContainerImage(e.target.value)}
              placeholder="ghcr.io/yourname/janus-implementation:latest"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-[#F3F4F6] placeholder-[#6B7280]
                       focus:outline-none focus:border-[#63D297]/50"
              required
            />
            <p className="text-xs text-[#6B7280]">
              Container will be run in a Sandy sandbox for evaluation
            </p>
          </div>
        )}

        <div className="space-y-3">
          <label className="text-sm text-[#9CA3AF]">Benchmark Suite</label>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {SUITES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setSuite(s.value)}
                className={`p-4 rounded-lg border text-left transition ${
                  suite === s.value
                    ? 'border-[#63D297] bg-[#63D297]/10'
                    : 'border-white/10 hover:border-white/20'
                }`}
              >
                <div className="flex justify-between items-start">
                  <span className="font-medium text-[#F3F4F6]">{s.label}</span>
                  <span className="text-xs text-[#6B7280]">{s.duration}</span>
                </div>
                <p className="text-xs text-[#9CA3AF] mt-1">{s.description}</p>
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="model" className="text-sm text-[#9CA3AF]">
            Model (for tool metadata)
          </label>
          <select
            id="model"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                     text-[#F3F4F6] focus:outline-none focus:border-[#63D297]/50"
          >
            <option value="deepseek-reasoner">DeepSeek Reasoner</option>
            <option value="gpt-4o">GPT-4o</option>
            <option value="claude-3-sonnet">Claude 3 Sonnet</option>
            <option value="custom">Custom</option>
          </select>
          {model === 'custom' && (
            <input
              type="text"
              value={customModel}
              onChange={(e) => setCustomModel(e.target.value)}
              placeholder="your-model-name"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg
                       text-[#F3F4F6] placeholder-[#6B7280]
                       focus:outline-none focus:border-[#63D297]/50"
              required
            />
          )}
        </div>

        {error && (
          <div
            className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400"
            role="alert"
            aria-live="polite"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-4 rounded-lg bg-[#63D297] text-[#0F1419] font-semibold
                   hover:bg-[#63D297]/90 disabled:opacity-50 disabled:cursor-not-allowed
                   transition"
        >
          {isSubmitting ? 'Starting Run...' : 'Start Scoring Run'}
        </button>
      </form>
    </section>
  );
}
