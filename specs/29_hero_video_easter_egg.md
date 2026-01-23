# Spec 29: Hero Video Easter Egg

## Status: COMPLETE

## Context / Why

The landing page hero section features a static image of Janus riding a bull. There's also a generated video file (`Janus_God_and_Bull_Video_Generation.mp4`) in the public folder that shows an animated version of this scene.

Adding an easter egg where clicking the hero image plays this video creates a delightful surprise for users and showcases the AI-generated video capabilities relevant to Janus.

## Goals

- Add click-to-play video easter egg on hero image
- Create smooth, polished video playback experience
- Keep the easter egg subtle (no obvious UI hints)
- Maintain the existing hero section appearance when video is not playing

## Non-Goals

- Auto-playing the video on page load
- Adding visible video controls or play button
- Changing the hero layout significantly

## Functional Requirements

### FR-1: Make Hero Image Clickable

Convert the hero image to a clickable element:

```tsx
// HeroSection.tsx
'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';

export function HeroSection() {
  const [showVideo, setShowVideo] = useState(false);

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />

      <div className="hero-image-stage">
        <div
          className="hero-image-frame cursor-pointer"
          onClick={() => setShowVideo(true)}
          role="button"
          aria-label="Play video"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && setShowVideo(true)}
        >
          <Image
            src="/hero-img2.png"
            alt="Janus riding an iridescent bull"
            fill
            priority
            sizes="100vw"
            className="hero-image"
          />
          <div className="hero-image-glow" />
          <div className="hero-image-rim" />
        </div>
      </div>

      {/* Video Modal */}
      {showVideo && (
        <HeroVideoModal onClose={() => setShowVideo(false)} />
      )}

      {/* ... rest of hero content ... */}
    </section>
  );
}
```

### FR-2: Create Video Modal Component

Create a fullscreen video modal overlay:

```tsx
// components/landing/HeroVideoModal.tsx
'use client';

import { useEffect, useRef, useCallback } from 'react';

interface HeroVideoModalProps {
  onClose: () => void;
}

export function HeroVideoModal({ onClose }: HeroVideoModalProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  // Close on escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Auto-play when mounted
  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      video.play().catch(console.error);
    }
  }, []);

  // Close when video ends
  const handleEnded = useCallback(() => {
    onClose();
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Video player"
    >
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 text-white/60 hover:text-white transition-colors z-10"
        aria-label="Close video"
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Video container */}
      <div
        className="relative w-full max-w-4xl mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <video
          ref={videoRef}
          src="/Janus_God_and_Bull_Video_Generation.mp4"
          className="w-full rounded-2xl shadow-2xl"
          controls={false}
          playsInline
          onEnded={handleEnded}
          onClick={() => {
            const video = videoRef.current;
            if (video) {
              video.paused ? video.play() : video.pause();
            }
          }}
        />

        {/* Subtle glow effect */}
        <div className="absolute -inset-4 bg-[#63D297]/10 blur-3xl -z-10 rounded-full" />
      </div>
    </div>
  );
}
```

### FR-3: Add Hover Effect (Subtle Hint)

Add a subtle hover effect to hint at interactivity without being too obvious:

```css
/* In globals.css */
.hero-image-frame {
  /* existing styles */
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.hero-image-frame:hover {
  transform: scale(1.02);
  box-shadow: 0 0 40px rgba(99, 210, 151, 0.2);
}

.hero-image-frame:active {
  transform: scale(0.98);
}
```

### FR-4: Export Component

Add the modal to the component exports:

```tsx
// components/landing/index.ts
export { HeroVideoModal } from './HeroVideoModal';
```

## Non-Functional Requirements

### NFR-1: Performance

- Video should start playing within 500ms of click
- Modal should open/close smoothly (CSS transitions)
- No layout shift when modal opens

### NFR-2: Accessibility

- Modal can be closed with Escape key
- Focus trapped in modal while open
- Proper ARIA attributes
- Click outside to close

### NFR-3: Mobile Support

- Video plays inline on mobile (no fullscreen hijack)
- Touch-friendly close button
- Responsive sizing

## Acceptance Criteria

- [ ] Clicking hero image opens video modal
- [ ] Video auto-plays when modal opens
- [ ] Clicking outside video closes modal
- [ ] Pressing Escape closes modal
- [ ] Video ends → modal closes automatically
- [ ] Clicking video toggles play/pause
- [ ] Subtle hover effect on hero image
- [ ] Works on mobile devices
- [ ] No visible play button or hint (easter egg style)

## Files to Modify

- `ui/src/components/landing/HeroSection.tsx` - Add click handler and state
- `ui/src/components/landing/HeroVideoModal.tsx` - Create new component
- `ui/src/components/landing/index.ts` - Export new component
- `ui/src/app/globals.css` - Add hover styles

## Video File

The video file already exists at:
- `ui/public/Janus_God_and_Bull_Video_Generation.mp4` (1.8 MB)

## Related Specs

- Spec 18: Landing Page (original implementation)
- Spec 22: UI Polish
