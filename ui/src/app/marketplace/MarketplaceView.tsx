'use client';

import { useMemo, useState } from 'react';
import componentsData from './data/components.json';
import { Component } from './components/types';
import { MarketplaceHero } from './components/MarketplaceHero';
import { MarketplaceFilters, SortOption } from './components/MarketplaceFilters';
import { CategoryFilterValue } from './components/CategoryFilter';
import { ComponentGrid } from './components/ComponentGrid';
import { ComponentDetailModal } from './components/ComponentDetailModal';
import { HowItWorks } from './components/HowItWorks';
import { SubmissionSection } from './components/SubmissionSection';
import { InspirationSection } from './components/InspirationSection';
import { MarketplaceFAQ } from './components/MarketplaceFAQ';

const components = componentsData as Component[];

const sorters: Record<SortOption, (a: Component, b: Component) => number> = {
  popular: (a, b) => b.usageCount - a.usageCount,
  newest: (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  rating: (a, b) => (b.rating ?? 0) - (a.rating ?? 0),
  earnings: (a, b) => (b.earnings ?? 0) - (a.earnings ?? 0),
};

export function MarketplaceView() {
  const [activeCategory, setActiveCategory] = useState<CategoryFilterValue>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOption, setSortOption] = useState<SortOption>('popular');
  const [selectedComponent, setSelectedComponent] = useState<Component | null>(null);

  const filteredComponents = useMemo(() => {
    let filtered = components;

    if (activeCategory !== 'all') {
      filtered = filtered.filter((component) => component.category === activeCategory);
    }

    const normalizedSearch = searchTerm.trim().toLowerCase();
    if (normalizedSearch) {
      filtered = filtered.filter((component) => {
        const tags = component.tags.join(' ').toLowerCase();
        return (
          component.name.toLowerCase().includes(normalizedSearch) ||
          component.description.toLowerCase().includes(normalizedSearch) ||
          component.author.toLowerCase().includes(normalizedSearch) ||
          tags.includes(normalizedSearch)
        );
      });
    }

    return [...filtered].sort(sorters[sortOption]);
  }, [activeCategory, searchTerm, sortOption]);

  return (
    <main className="flex-1">
      <MarketplaceHero />

      <section className="py-16 lg:py-24" id="components">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Component library
              </p>
              <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
                Discover the building blocks
              </h2>
              <p className="text-[#9CA3AF] max-w-2xl">
                Browse reusable agents, tools, and memory systems. Filter by
                category, compare ratings, and open integration guides instantly.
              </p>
            </div>
          </div>

          <MarketplaceFilters
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
            searchTerm={searchTerm}
            onSearchChange={setSearchTerm}
            sortOption={sortOption}
            onSortChange={setSortOption}
            resultCount={filteredComponents.length}
          />

          <ComponentGrid
            components={filteredComponents}
            onSelect={setSelectedComponent}
          />
        </div>
      </section>

      <HowItWorks />
      <SubmissionSection />
      <InspirationSection />
      <MarketplaceFAQ />

      <ComponentDetailModal
        component={selectedComponent}
        onClose={() => setSelectedComponent(null)}
      />
    </main>
  );
}
