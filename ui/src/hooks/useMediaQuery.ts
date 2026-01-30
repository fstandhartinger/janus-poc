import { useState, useEffect } from 'react';

/**
 * Hook to detect if a media query matches.
 * Returns false during SSR and initial render, then updates to match the query.
 *
 * @param query - CSS media query string (e.g., '(min-width: 1024px)')
 * @returns boolean indicating if the media query matches
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);

    // Set initial value
    setMatches(media.matches);

    // Listen for changes
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);

    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
}
