'use client';

interface CitationProps {
  index: number;
  url: string;
  title?: string;
}

export function Citation({ index, url, title }: CitationProps) {
  return (
    <span className="citation">
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="citation-button"
        aria-label={`Open citation ${index}`}
      >
        {index}
      </a>
      <span className="citation-tooltip" role="tooltip">
        <span className="citation-tooltip-title">{title || url}</span>
        <span className="citation-tooltip-url">{url}</span>
      </span>
    </span>
  );
}
