import { CodeBlock } from '@/components/CodeBlock';

const artifactExample = `{
  "message": {
    "content": "I've created the chart you requested.",
    "artifacts": [
      {
        "id": "artf_x7k9m2p4",
        "type": "image",
        "mime_type": "image/png",
        "display_name": "sales_chart.png",
        "size_bytes": 45678,
        "url": "https://janus-gateway.../v1/artifacts/artf_x7k9m2p4",
        "ttl_seconds": 3600
      }
    ]
  }
}`;

const generativeUiExample = `Here's an interactive calculator:

\`\`\`html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #1a1a2e; color: #e0e0e0; padding: 1rem; }
  </style>
</head>
<body>
  <input type="number" id="a"> + <input type="number" id="b">
  <button onclick="calculate()">Calculate</button>
  <p id="result"></p>
  <script>
    function calculate() {
      const a = parseFloat(document.getElementById('a').value) || 0;
      const b = parseFloat(document.getElementById('b').value) || 0;
      document.getElementById('result').textContent = 'Result: ' + (a + b);
    }
  </script>
</body>
</html>
\`\`\`
`;

const reasoningExample = `{
  "message": {
    "content": "The answer is 42.",
    "reasoning_content": "Let me break this down step by step..."
  }
}`;

const streamEventExample = `{
  "delta": {
    "content": null,
    "janus": {
      "event": "tool_start",
      "tool_name": "web_search",
      "metadata": {"query": "latest AI news"}
    }
  }
}`;

export function JanusExtensions() {
  return (
    <div className="space-y-4">
      <details open className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Artifacts
        </summary>
        <div className="mt-4 space-y-4 text-sm text-[#D1D5DB]">
          <p>
            When the model generates files, images, or other non-text outputs, they appear in the
            <span className="font-mono"> artifacts</span> array.
          </p>
          <CodeBlock code={artifactExample} language="json" />
          <div className="grid sm:grid-cols-2 gap-3 text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
            <div>image - Generated images (PNG, JPEG, WebP)</div>
            <div>file - Documents, code, data files</div>
            <div>dataset - Structured data collections</div>
            <div>binary - Raw binary outputs</div>
          </div>
          <p className="text-xs text-[#9CA3AF]">
            Artifacts under 1MB are returned as data URLs. Larger files use artifact URLs.
          </p>
        </div>
      </details>

      <details className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Generative UI blocks
        </summary>
        <div className="mt-4 space-y-4 text-sm text-[#D1D5DB]">
          <p>
            Responses may contain interactive UI widgets using the
            <span className="font-mono"> html-gen-ui</span> code fence. These blocks render as
            sandboxed iframes in the Janus chat UI.
          </p>
          <CodeBlock code={generativeUiExample} language="markdown" />
        </div>
      </details>

      <details className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Reasoning content
        </summary>
        <div className="mt-4 space-y-4 text-sm text-[#D1D5DB]">
          <p>
            Complex tasks may include intermediate reasoning steps in the
            <span className="font-mono"> reasoning_content</span> field.
          </p>
          <CodeBlock code={reasoningExample} language="json" />
        </div>
      </details>

      <details className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Janus stream events
        </summary>
        <div className="mt-4 space-y-4 text-sm text-[#D1D5DB]">
          <p>
            During streaming, special events may appear in the
            <span className="font-mono"> janus</span> field.
          </p>
          <CodeBlock code={streamEventExample} language="json" />
          <div className="grid sm:grid-cols-2 gap-3 text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
            <div>tool_start / tool_end - Tool execution lifecycle</div>
            <div>sandbox_start / sandbox_end - Agent sandbox execution</div>
            <div>artifact_generated - New artifact created</div>
          </div>
        </div>
      </details>
    </div>
  );
}
