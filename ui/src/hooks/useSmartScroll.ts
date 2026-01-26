'use client';

import { useCallback, useEffect, useRef } from 'react';
import type { RefObject } from 'react';

export function useSmartScroll<T extends HTMLElement>(
  containerRef: RefObject<T | null>,
  deps: unknown[]
) {
  const isNearBottom = useRef(true);
  const userScrolledUp = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      isNearBottom.current = distanceFromBottom < 100;

      if (distanceFromBottom > 200) {
        userScrolledUp.current = true;
      } else if (distanceFromBottom < 80) {
        userScrolledUp.current = false;
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();

    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [containerRef]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    if (isNearBottom.current && !userScrolledUp.current) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, deps);

  const resetUserScroll = useCallback(() => {
    userScrolledUp.current = false;
    isNearBottom.current = true;
  }, []);

  return { resetUserScroll };
}
