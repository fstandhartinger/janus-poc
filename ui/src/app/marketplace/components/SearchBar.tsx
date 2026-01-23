interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
  return (
    <label className="search-input w-full">
      <span className="text-[#9CA3AF]" aria-hidden>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <line x1="16.65" y1="16.65" x2="21" y2="21" />
        </svg>
      </span>
      <input
        type="text"
        placeholder="Search components, tags, or authors"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label="Search components"
      />
    </label>
  );
}
