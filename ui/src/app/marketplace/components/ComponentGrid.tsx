import { Component } from './types';
import { ComponentCard } from './ComponentCard';

interface ComponentGridProps {
  components: Component[];
  onSelect: (component: Component) => void;
}

export function ComponentGrid({ components, onSelect }: ComponentGridProps) {
  if (components.length === 0) {
    return (
      <div className="glass-card p-8 text-center text-[#9CA3AF]">
        No components match your filters yet. Try a different category or search.
      </div>
    );
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {components.map((component) => (
        <ComponentCard
          key={component.id}
          component={component}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
