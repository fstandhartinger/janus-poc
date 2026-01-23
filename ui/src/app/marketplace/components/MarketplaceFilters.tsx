import { CategoryFilter, CategoryFilterValue } from './CategoryFilter';
import { SearchBar } from './SearchBar';

export type SortOption = 'popular' | 'newest' | 'rating' | 'earnings';

const sortOptions: Array<{ value: SortOption; label: string }> = [
  { value: 'popular', label: 'Most Popular' },
  { value: 'newest', label: 'Newest' },
  { value: 'rating', label: 'Highest Rated' },
  { value: 'earnings', label: 'Most Earnings' },
];

interface MarketplaceFiltersProps {
  activeCategory: CategoryFilterValue;
  onCategoryChange: (category: CategoryFilterValue) => void;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  sortOption: SortOption;
  onSortChange: (value: SortOption) => void;
  resultCount: number;
}

export function MarketplaceFilters({
  activeCategory,
  onCategoryChange,
  searchTerm,
  onSearchChange,
  sortOption,
  onSortChange,
  resultCount,
}: MarketplaceFiltersProps) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        <div className="flex-1">
          <SearchBar value={searchTerm} onChange={onSearchChange} />
        </div>
        <div className="glass px-4 py-2 rounded-full text-sm text-[#D1D5DB] flex items-center gap-3">
          <span className="text-[#9CA3AF]">Sort by</span>
          <select
            value={sortOption}
            onChange={(event) => onSortChange(event.target.value as SortOption)}
            className="bg-transparent text-[#F3F4F6] text-sm focus:outline-none"
            aria-label="Sort components"
          >
            {sortOptions.map((option) => (
              <option key={option.value} value={option.value} className="bg-[#0B0F14]">
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <CategoryFilter activeCategory={activeCategory} onChange={onCategoryChange} />
        <span className="text-sm text-[#9CA3AF]">
          Showing {resultCount} components
        </span>
      </div>
    </div>
  );
}
