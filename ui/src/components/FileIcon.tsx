import type { ReactElement } from 'react';
import type { FileCategory } from '@/lib/file-types';

interface FileIconProps {
  category: FileCategory;
  className?: string;
}

const iconProps = (className?: string) => ({
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  className,
  'aria-hidden': true,
});

function FileTextIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <path d="M6 2h7l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" />
      <path d="M13 2v6h6" />
      <path d="M8 13h8M8 17h8M8 9h4" />
    </svg>
  );
}

function ImageIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="M3 15l5-5 4 4 5-6 4 7" />
      <circle cx="8.5" cy="9" r="1.5" />
    </svg>
  );
}

function TableIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 4v16M15 4v16" />
    </svg>
  );
}

function PresentationIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M12 16v4M8 20h8" />
      <path d="M7 8h10M7 11h6" />
    </svg>
  );
}

function CodeIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <path d="M8 9l-4 3 4 3" />
      <path d="M16 9l4 3-4 3" />
      <path d="M10 19l4-14" />
    </svg>
  );
}

function DatabaseIcon({ className }: { className?: string }) {
  return (
    <svg {...iconProps(className)}>
      <ellipse cx="12" cy="5" rx="7" ry="3" />
      <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
      <path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
    </svg>
  );
}

const ICONS: Record<FileCategory, ({ className }: { className?: string }) => ReactElement> = {
  images: ImageIcon,
  pdf: FileTextIcon,
  word: FileTextIcon,
  excel: TableIcon,
  powerpoint: PresentationIcon,
  text: FileTextIcon,
  code: CodeIcon,
  data: DatabaseIcon,
};

export function FileIcon({ category, className }: FileIconProps) {
  const Icon = ICONS[category] ?? FileTextIcon;
  return <Icon className={className} />;
}
