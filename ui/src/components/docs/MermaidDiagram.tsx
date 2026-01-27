import { MermaidDiagram as BaseMermaidDiagram } from '@/components/MermaidDiagram';

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  ariaLabel?: string;
}

export function MermaidDiagram({ chart, className, ariaLabel }: MermaidDiagramProps) {
  return (
    <div className={`glass-card p-6 rounded-xl overflow-auto ${className ?? ''}`.trim()}>
      <BaseMermaidDiagram chart={chart} ariaLabel={ariaLabel} clickable={false} />
    </div>
  );
}
