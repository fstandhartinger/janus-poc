# Spec 48: Rich Data Visualization

## Status: COMPLETE

## Context / Why

The agent often needs to present data in visual formats beyond plain text:

- **Charts**: Line, bar, pie charts for numerical data
- **Spreadsheets**: Tabular data with sorting/filtering
- **Diagrams**: Flowcharts, sequence diagrams, mind maps
- **Code**: Syntax-highlighted code blocks with copy button

This spec adds rich visualization components that the agent can generate inline.

## Goals

- Support multiple visualization types in chat responses
- Render charts using a lightweight charting library
- Display interactive spreadsheets/tables
- Render diagrams from Mermaid markdown
- Provide syntax-highlighted code with copy functionality

## Non-Goals

- Full spreadsheet editing (Google Sheets clone)
- 3D visualizations
- Real-time data streaming visualizations

## Functional Requirements

### FR-1: Visualization Protocol

Define a protocol for embedding visualizations in responses:

```markdown
<!-- In assistant message content -->

Here's your sales data:

:::chart
{
  "type": "bar",
  "data": {
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [{
      "label": "Revenue",
      "data": [12000, 19000, 15000, 22000]
    }]
  }
}
:::

And the detailed breakdown:

:::spreadsheet
[
  ["Product", "Q1", "Q2", "Q3", "Q4"],
  ["Widget A", 4000, 6000, 5000, 8000],
  ["Widget B", 5000, 8000, 6000, 9000],
  ["Widget C", 3000, 5000, 4000, 5000]
]
:::

The process flow:

:::diagram
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Process]
    B -->|No| D[Skip]
    C --> E[End]
    D --> E
:::
```

### FR-2: Chart Component

```tsx
// ui/src/components/viz/ChartBlock.tsx

'use client';

import { useEffect, useRef } from 'react';
import {
  Chart,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

// Register Chart.js components
Chart.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'doughnut';
  data: {
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
    }>;
  };
  options?: Record<string, unknown>;
}

interface ChartBlockProps {
  config: ChartData;
}

// Chutes design system colors
const CHART_COLORS = [
  '#63D297', // Moss green (primary)
  '#FA5D19', // Tomato orange
  '#3B82F6', // Blue
  '#8B5CF6', // Purple
  '#F59E0B', // Amber
  '#EC4899', // Pink
];

export function ChartBlock({ config }: ChartBlockProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;

    // Destroy existing chart
    if (chartRef.current) {
      chartRef.current.destroy();
    }

    // Apply default colors if not provided
    const datasets = config.data.datasets.map((dataset, i) => ({
      ...dataset,
      backgroundColor: dataset.backgroundColor || CHART_COLORS[i % CHART_COLORS.length],
      borderColor: dataset.borderColor || CHART_COLORS[i % CHART_COLORS.length],
    }));

    // Create chart
    chartRef.current = new Chart(canvasRef.current, {
      type: config.type,
      data: {
        ...config.data,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            labels: {
              color: '#9CA3AF',
            },
          },
        },
        scales: config.type !== 'pie' && config.type !== 'doughnut' ? {
          x: {
            ticks: { color: '#9CA3AF' },
            grid: { color: '#1F2937' },
          },
          y: {
            ticks: { color: '#9CA3AF' },
            grid: { color: '#1F2937' },
          },
        } : undefined,
        ...config.options,
      },
    });

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [config]);

  return (
    <div className="chart-block">
      <canvas ref={canvasRef} />
    </div>
  );
}
```

### FR-3: Spreadsheet Component

```tsx
// ui/src/components/viz/SpreadsheetBlock.tsx

'use client';

import { useState, useMemo } from 'react';

type CellValue = string | number | boolean | null;
type Row = CellValue[];
type SpreadsheetData = Row[];

interface SpreadsheetBlockProps {
  data: SpreadsheetData;
  hasHeader?: boolean;
}

export function SpreadsheetBlock({ data, hasHeader = true }: SpreadsheetBlockProps) {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filter, setFilter] = useState('');

  const headers = hasHeader ? data[0] : null;
  const rows = hasHeader ? data.slice(1) : data;

  const filteredRows = useMemo(() => {
    if (!filter.trim()) return rows;

    const query = filter.toLowerCase();
    return rows.filter((row) =>
      row.some((cell) =>
        String(cell).toLowerCase().includes(query)
      )
    );
  }, [rows, filter]);

  const sortedRows = useMemo(() => {
    if (sortColumn === null) return filteredRows;

    return [...filteredRows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle numbers
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // Handle strings
      const aStr = String(aVal ?? '');
      const bStr = String(bVal ?? '');
      const cmp = aStr.localeCompare(bStr);
      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [filteredRows, sortColumn, sortDirection]);

  const handleSort = (colIndex: number) => {
    if (sortColumn === colIndex) {
      setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(colIndex);
      setSortDirection('asc');
    }
  };

  const copyToClipboard = () => {
    const tsv = data.map((row) => row.join('\t')).join('\n');
    navigator.clipboard.writeText(tsv);
  };

  const downloadCSV = () => {
    const csv = data.map((row) =>
      row.map((cell) => {
        const str = String(cell ?? '');
        // Escape quotes and wrap in quotes if needed
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
          return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
      }).join(',')
    ).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="spreadsheet-block">
      <div className="spreadsheet-toolbar">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter..."
          className="spreadsheet-filter"
        />
        <div className="spreadsheet-actions">
          <button onClick={copyToClipboard} title="Copy to clipboard">
            <CopyIcon />
          </button>
          <button onClick={downloadCSV} title="Download CSV">
            <DownloadIcon />
          </button>
        </div>
      </div>

      <div className="spreadsheet-scroll">
        <table className="spreadsheet-table">
          {headers && (
            <thead>
              <tr>
                {headers.map((header, i) => (
                  <th
                    key={i}
                    onClick={() => handleSort(i)}
                    className="spreadsheet-header"
                  >
                    <span>{String(header)}</span>
                    {sortColumn === i && (
                      <span className="sort-indicator">
                        {sortDirection === 'asc' ? '▲' : '▼'}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {sortedRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="spreadsheet-cell">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="spreadsheet-footer">
        {sortedRows.length} rows
        {filter && ` (filtered from ${rows.length})`}
      </div>
    </div>
  );
}

function formatCell(value: CellValue): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    // Format large numbers with commas
    return value.toLocaleString();
  }
  return String(value);
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
```

### FR-4: Diagram Component (Mermaid)

```tsx
// ui/src/components/viz/DiagramBlock.tsx

'use client';

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  themeVariables: {
    primaryColor: '#63D297',
    primaryTextColor: '#F3F4F6',
    primaryBorderColor: '#1F2937',
    lineColor: '#6B7280',
    secondaryColor: '#1F2937',
    tertiaryColor: '#111827',
  },
  flowchart: {
    htmlLabels: true,
    curve: 'basis',
  },
});

interface DiagramBlockProps {
  code: string;
}

export function DiagramBlock({ code }: DiagramBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string>('');

  useEffect(() => {
    const renderDiagram = async () => {
      if (!containerRef.current) return;

      try {
        setError(null);
        const id = `mermaid-${Math.random().toString(36).slice(2)}`;
        const { svg } = await mermaid.render(id, code);
        setSvg(svg);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      }
    };

    renderDiagram();
  }, [code]);

  const downloadSVG = () => {
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'diagram.svg';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="diagram-error">
        <span>Diagram Error: {error}</span>
        <pre className="diagram-source">{code}</pre>
      </div>
    );
  }

  return (
    <div className="diagram-block">
      <div className="diagram-toolbar">
        <button onClick={downloadSVG} title="Download SVG">
          <DownloadIcon /> SVG
        </button>
      </div>
      <div
        ref={containerRef}
        className="diagram-content"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
```

### FR-5: Content Parser & Renderer

```tsx
// ui/src/components/viz/RichContent.tsx

'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { ChartBlock } from './ChartBlock';
import { SpreadsheetBlock } from './SpreadsheetBlock';
import { DiagramBlock } from './DiagramBlock';

interface RichContentProps {
  content: string;
}

// Parse custom blocks from content
function parseCustomBlocks(content: string): Array<{ type: string; content: string }> {
  const blocks: Array<{ type: string; content: string }> = [];
  const blockRegex = /:::(\w+)\n([\s\S]*?)\n:::/g;

  let lastIndex = 0;
  let match;

  while ((match = blockRegex.exec(content)) !== null) {
    // Add text before block
    if (match.index > lastIndex) {
      blocks.push({
        type: 'markdown',
        content: content.slice(lastIndex, match.index),
      });
    }

    // Add the custom block
    blocks.push({
      type: match[1],
      content: match[2].trim(),
    });

    lastIndex = match.index + match[0].length;
  }

  // Add remaining text
  if (lastIndex < content.length) {
    blocks.push({
      type: 'markdown',
      content: content.slice(lastIndex),
    });
  }

  return blocks;
}

export function RichContent({ content }: RichContentProps) {
  const blocks = parseCustomBlocks(content);

  return (
    <div className="rich-content">
      {blocks.map((block, index) => {
        switch (block.type) {
          case 'chart':
            try {
              const config = JSON.parse(block.content);
              return <ChartBlock key={index} config={config} />;
            } catch {
              return <div key={index} className="parse-error">Invalid chart data</div>;
            }

          case 'spreadsheet':
            try {
              const data = JSON.parse(block.content);
              return <SpreadsheetBlock key={index} data={data} />;
            } catch {
              return <div key={index} className="parse-error">Invalid spreadsheet data</div>;
            }

          case 'diagram':
            return <DiagramBlock key={index} code={block.content} />;

          case 'markdown':
          default:
            return (
              <ReactMarkdown
                key={index}
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    const codeString = String(children).replace(/\n$/, '');

                    if (!inline && match) {
                      return (
                        <div className="code-block">
                          <div className="code-header">
                            <span className="code-language">{match[1]}</span>
                            <button
                              onClick={() => navigator.clipboard.writeText(codeString)}
                              className="code-copy"
                            >
                              Copy
                            </button>
                          </div>
                          <SyntaxHighlighter
                            style={oneDark}
                            language={match[1]}
                            PreTag="div"
                            {...props}
                          >
                            {codeString}
                          </SyntaxHighlighter>
                        </div>
                      );
                    }

                    return (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {block.content}
              </ReactMarkdown>
            );
        }
      })}
    </div>
  );
}
```

### FR-6: Visualization Styles

```css
/* ui/src/app/globals.css */

/* Chart Block */
.chart-block {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  padding: 1rem;
  margin: 1rem 0;
}

/* Spreadsheet Block */
.spreadsheet-block {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  overflow: hidden;
  margin: 1rem 0;
}

.spreadsheet-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border-color);
  gap: 0.5rem;
}

.spreadsheet-filter {
  flex: 1;
  max-width: 200px;
  padding: 0.375rem 0.5rem;
  background: var(--input-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.375rem;
  color: var(--text-primary);
  font-size: 0.75rem;
}

.spreadsheet-actions {
  display: flex;
  gap: 0.25rem;
}

.spreadsheet-actions button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 0.25rem;
}

.spreadsheet-actions button:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.spreadsheet-scroll {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.spreadsheet-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.spreadsheet-header {
  position: sticky;
  top: 0;
  background: var(--card-bg);
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 600;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border-color);
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
}

.spreadsheet-header:hover {
  background: var(--card-bg-hover);
}

.sort-indicator {
  margin-left: 0.25rem;
  font-size: 0.625rem;
  opacity: 0.6;
}

.spreadsheet-cell {
  padding: 0.375rem 0.75rem;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  white-space: nowrap;
}

.spreadsheet-table tbody tr:hover .spreadsheet-cell {
  background: var(--card-bg-hover);
}

.spreadsheet-footer {
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  border-top: 1px solid var(--border-color);
}

/* Diagram Block */
.diagram-block {
  background: var(--card-bg);
  border: 1px solid var(--border-color);
  border-radius: 0.75rem;
  overflow: hidden;
  margin: 1rem 0;
}

.diagram-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 0.5rem;
  border-bottom: 1px solid var(--border-color);
}

.diagram-toolbar button {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.5rem;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.diagram-toolbar button:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

.diagram-content {
  padding: 1rem;
  display: flex;
  justify-content: center;
  overflow-x: auto;
}

.diagram-content svg {
  max-width: 100%;
  height: auto;
}

.diagram-error {
  padding: 1rem;
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: 0.75rem;
  color: var(--error-text);
  margin: 1rem 0;
}

.diagram-source {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: var(--card-bg);
  border-radius: 0.25rem;
  font-size: 0.75rem;
  overflow-x: auto;
}

/* Code Block */
.code-block {
  margin: 1rem 0;
  border-radius: 0.75rem;
  overflow: hidden;
  border: 1px solid var(--border-color);
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  background: var(--card-bg);
  border-bottom: 1px solid var(--border-color);
}

.code-language {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

.code-copy {
  padding: 0.25rem 0.5rem;
  background: none;
  border: 1px solid var(--border-color);
  border-radius: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  cursor: pointer;
}

.code-copy:hover {
  background: var(--card-bg-hover);
  color: var(--text-primary);
}

/* Parse Error */
.parse-error {
  padding: 0.75rem;
  background: var(--error-bg);
  border: 1px solid var(--error-border);
  border-radius: 0.5rem;
  color: var(--error-text);
  font-size: 0.875rem;
}
```

### FR-7: Agent Documentation

```markdown
# docs/models/data-visualization.md

## Generating Rich Visualizations

You can include charts, spreadsheets, and diagrams in your responses using special blocks.

### Charts

Use `:::chart` blocks with Chart.js configuration:

```
:::chart
{
  "type": "bar",
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [{
      "label": "Sales",
      "data": [100, 150, 200]
    }]
  }
}
:::
```

Supported chart types: bar, line, pie, doughnut

### Spreadsheets

Use `:::spreadsheet` blocks with 2D array data:

```
:::spreadsheet
[
  ["Name", "Age", "City"],
  ["Alice", 30, "New York"],
  ["Bob", 25, "Los Angeles"]
]
:::
```

First row is treated as header. Users can sort and filter the data.

### Diagrams

Use `:::diagram` blocks with Mermaid syntax:

```
:::diagram
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[Skip]
:::
```

Supports: flowcharts, sequence diagrams, class diagrams, etc.
See https://mermaid.js.org/syntax/ for full syntax reference.
```

## Non-Functional Requirements

### NFR-1: Performance

- Chart rendering < 100ms
- Spreadsheet with 1000 rows should be responsive
- Diagram rendering < 500ms

### NFR-2: Accessibility

- Charts have screen reader descriptions
- Tables are navigable with keyboard
- Color contrast meets WCAG guidelines

### NFR-3: Mobile

- Visualizations resize responsively
- Horizontal scroll for wide tables/diagrams
- Touch-friendly controls

## Acceptance Criteria

- [ ] Bar/line/pie charts rendering correctly
- [ ] Spreadsheet with sort/filter working
- [ ] Mermaid diagrams rendering correctly
- [ ] Code blocks with syntax highlighting working
- [ ] Copy/download functionality working
- [ ] Dark theme applied to all visualizations
- [ ] Mobile-responsive layouts
- [ ] Agent documentation available

## Files to Modify/Create

```
ui/
└── src/
    └── components/
        └── viz/
            ├── ChartBlock.tsx        # NEW - Chart component
            ├── SpreadsheetBlock.tsx  # NEW - Spreadsheet component
            ├── DiagramBlock.tsx      # NEW - Diagram component
            ├── RichContent.tsx       # NEW - Content parser
            └── index.ts              # NEW - Exports
        └── MessageBubble.tsx         # MODIFY - Use RichContent
    └── app/
        └── globals.css               # MODIFY - Add viz styles

baseline-agent-cli/
└── agent-pack/
    └── models/
        └── data-visualization.md     # NEW - Agent docs
```

## Dependencies

```json
// ui/package.json
{
  "chart.js": "^4.4.0",
  "mermaid": "^10.6.0",
  "react-markdown": "^9.0.0",
  "remark-gfm": "^4.0.0",
  "react-syntax-highlighter": "^15.5.0"
}
```

## Related Specs

- `specs/11_chat_ui.md` - Chat UI integration
- `specs/49_canvas_feature.md` - Canvas for editing visualizations

NR_OF_TRIES=1
