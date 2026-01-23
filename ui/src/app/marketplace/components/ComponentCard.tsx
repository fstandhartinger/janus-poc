import { Component, ComponentCategory, ComponentStatus } from './types';

const categoryStyles: Record<ComponentCategory, string> = {
  research: 'bg-[#3B82F6]/15 text-[#93C5FD]',
  coding: 'bg-[#63D297]/15 text-[#63D297]',
  memory: 'bg-[#8B5CF6]/15 text-[#C4B5FD]',
  tools: 'bg-[#F59E0B]/15 text-[#FCD34D]',
  models: 'bg-[#FA5D19]/15 text-[#FDBA74]',
};

const categoryLabels: Record<ComponentCategory, string> = {
  research: 'Research',
  coding: 'Coding',
  memory: 'Memory',
  tools: 'Tools',
  models: 'Models',
};

const statusStyles: Record<ComponentStatus, string> = {
  available: 'bg-[#63D297]/15 text-[#63D297]',
  coming_soon: 'bg-[#8B5CF6]/15 text-[#C4B5FD]',
  deprecated: 'bg-[#FA5D19]/15 text-[#FDBA74]',
};

const statusLabels: Record<ComponentStatus, string> = {
  available: 'Available',
  coming_soon: 'Coming Soon',
  deprecated: 'Deprecated',
};

function Star({ filled }: { filled: boolean }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill={filled ? '#FCD34D' : 'none'}
      stroke="#FCD34D"
      strokeWidth="1.5"
    >
      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
    </svg>
  );
}

interface ComponentCardProps {
  component: Component;
  onSelect: (component: Component) => void;
}

export function ComponentCard({ component, onSelect }: ComponentCardProps) {
  const rating = component.rating ?? 0;
  const filledStars = Math.floor(rating);

  return (
    <button
      type="button"
      onClick={() => onSelect(component)}
      className="component-card w-full text-left p-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#63D297]/60"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-4">
          <div className="component-card-thumbnail rounded-xl p-3">
            <img
              src={component.icon ?? '/marketplace/tools.svg'}
              alt=""
              loading="lazy"
              decoding="async"
              className="h-8 w-8"
            />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-[#F3F4F6]">
              {component.name}
            </h3>
            <p className="text-sm text-[#9CA3AF]">by {component.author}</p>
          </div>
        </div>
        <span
          className={`text-xs font-medium px-3 py-1 rounded-full ${statusStyles[component.status]}`}
        >
          {statusLabels[component.status]}
        </span>
      </div>

      <p className="mt-4 text-sm text-[#9CA3AF] leading-relaxed">
        {component.description}
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-[#9CA3AF]">
        <span className={`px-3 py-1 rounded-full ${categoryStyles[component.category]}`}>
          {categoryLabels[component.category]}
        </span>
        <span>Used by {component.usageCount} miners</span>
        <span>v{component.version}</span>
      </div>

      <div className="mt-4 flex items-center gap-2 text-xs text-[#9CA3AF]">
        {rating > 0 ? (
          <>
            <div className="flex items-center gap-1">
              {Array.from({ length: 5 }).map((_, index) => (
                <Star key={index} filled={index < filledStars} />
              ))}
            </div>
            <span>{rating.toFixed(1)}</span>
          </>
        ) : (
          <span>No ratings yet</span>
        )}
      </div>
    </button>
  );
}
