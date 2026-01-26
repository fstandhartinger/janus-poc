'use client';

import { useEffect, useRef, useState } from 'react';
import type { DebugEvent } from '@/types/debug';

interface DebugLogProps {
  events: DebugEvent[];
  correlationId?: string;
}

const typeClassMap: Record<string, string> = {
  error: 'debug-log-error',
  step: 'debug-log-step',
  tool: 'debug-log-tool',
  sandy: 'debug-log-sandy',
  prompt: 'debug-log-prompt',
};

function getEventCategory(eventType: string): string {
  if (eventType === 'error') return 'error';
  if (eventType.startsWith('tool_')) return 'tool';
  if (eventType.startsWith('sandy_')) return 'sandy';
  if (eventType.startsWith('prompt_')) return 'prompt';
  return 'step';
}

function formatDuration(startTime: Date, endTime: Date): string {
  const diff = endTime.getTime() - startTime.getTime();
  if (diff < 1000) return `${diff}ms`;
  if (diff < 60000) return `${(diff / 1000).toFixed(1)}s`;
  return `${Math.floor(diff / 60000)}m ${Math.floor((diff % 60000) / 1000)}s`;
}

export function DebugLog({ events, correlationId }: DebugLogProps) {
  const logRef = useRef<HTMLDivElement>(null);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  useEffect(() => {
    if (!logRef.current) return;
    logRef.current.scrollTo(0, logRef.current.scrollHeight);
  }, [events]);

  // Calculate total request duration
  const requestDuration =
    events.length > 1
      ? formatDuration(new Date(events[0].timestamp), new Date(events[events.length - 1].timestamp))
      : null;

  return (
    <div className="chat-debug-log-wrapper">
      {/* Header with correlation ID and timing */}
      <div className="chat-debug-log-header">
        {correlationId && (
          <span className="debug-log-correlation" title="Correlation ID">
            corr: {correlationId.slice(0, 12)}...
          </span>
        )}
        {requestDuration && (
          <span className="debug-log-duration" title="Total request duration">
            {requestDuration}
          </span>
        )}
        <span className="debug-log-count">{events.length} events</span>
      </div>

      {/* Event log */}
      <div ref={logRef} className="chat-debug-log">
        <div className="chat-debug-log-inner">
          {events.map((event, index) => {
            const timeLabel = formatTimestamp(event.timestamp);
            const category = getEventCategory(event.type);
            const toneClass = typeClassMap[category] || typeClassMap.step;
            const isExpanded = expandedIndex === index;
            const hasData = event.data && Object.keys(event.data).length > 0;

            return (
              <div
                key={`${event.timestamp}-${index}`}
                className={`debug-log-row ${toneClass} ${isExpanded ? 'expanded' : ''}`.trim()}
              >
                <div
                  className="debug-log-main"
                  onClick={() => hasData && setExpandedIndex(isExpanded ? null : index)}
                  role={hasData ? 'button' : undefined}
                  tabIndex={hasData ? 0 : undefined}
                >
                  <span className="debug-log-time">{timeLabel}</span>
                  <span className="debug-log-step">[{event.step}]</span>
                  <span className="debug-log-type">{event.type}</span>
                  <span className="debug-log-message">{event.message}</span>
                  {hasData && (
                    <span className="debug-log-expand-icon">{isExpanded ? '\u25BC' : '\u25B6'}</span>
                  )}
                </div>
                {isExpanded && hasData && (
                  <pre className="debug-log-data">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '--:--:--';
  }
  return date.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}
