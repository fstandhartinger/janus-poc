import { ComponentCategory } from './types';

export type CategoryFilterValue = ComponentCategory | 'all';

const categories: Array<{ value: CategoryFilterValue; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'research', label: 'Research' },
  { value: 'coding', label: 'Coding' },
  { value: 'memory', label: 'Memory' },
  { value: 'tools', label: 'Tools' },
  { value: 'models', label: 'Models' },
];

interface CategoryFilterProps {
  activeCategory: CategoryFilterValue;
  onChange: (category: CategoryFilterValue) => void;
}

export function CategoryFilter({ activeCategory, onChange }: CategoryFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((category) => {
        const isActive = activeCategory === category.value;
        return (
          <button
            key={category.value}
            type="button"
            onClick={() => onChange(category.value)}
            aria-pressed={isActive}
            className={`px-4 py-2 rounded-full text-sm font-medium transition border ${
              isActive
                ? 'bg-[#63D297]/15 text-[#63D297] border-[#63D297]/40'
                : 'bg-[#111726]/60 text-[#9CA3AF] border-[#1F2937] hover:border-[#374151] hover:text-[#E5E7EB]'
            }`}
          >
            {category.label}
          </button>
        );
      })}
    </div>
  );
}
