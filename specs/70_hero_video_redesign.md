# Spec 69: Hero Video Redesign - In-Place Playback with Scroll Control

## Status: DRAFT

## Context / Why

The current hero video implementation uses a click-triggered easter egg that opens a modal dialog. This creates a jarring user experience with:

1. Modal overlay obscures the page
2. Video appears in a different position/size than the hero image
3. No integration with page scroll behavior
4. Black video background contrasts with the page's aurora gradient background

The chutes-frontend project has an excellent implementation where:
- Video plays automatically and in-place
- After playing once, frames are extracted for scroll-controlled playback
- The video seamlessly blends with the page

We want to achieve similar behavior for the Janus landing page.

## Current State

**Video file**: `/ui/public/Janus_God_and_Bull_Video_Generation.mp4`
- Resolution: 1280x720 (16:9)
- Duration: 8 seconds
- Frame rate: 24 fps
- Has audio track (will be muted)
- **Issue**: VEO watermark in bottom-right corner
- **Issue**: Solid black background (hero image has transparency)

**Current implementation**:
- Hero image at `/ui/public/hero-img2.png`
- Click triggers `HeroVideoModal` component
- Modal plays video with controls=false
- Closes on video end or Escape key

## Goals

1. Auto-play video in-place after hero image loads
2. First frame aligns perfectly with hero image (no jump/resize)
3. Hide or remove VEO watermark
4. Blend black background with page gradient
5. Play once, then enable scroll-controlled frame scrubbing
6. Muted audio
7. Smooth visual transition from image → video → scroll control

## Functional Requirements

### FR-1: In-Place Video Component

Replace the modal approach with an in-place video that overlays the hero image:

```tsx
// ui/src/components/landing/HeroVideo.tsx

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import Image from 'next/image';

interface HeroVideoProps {
  onVideoReady?: () => void;
}

export function HeroVideo({ onVideoReady }: HeroVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const framesRef = useRef<ImageBitmap[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  const [imageLoaded, setImageLoaded] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [framesReady, setFramesReady] = useState(false);

  // Zoom and crop settings to hide watermark
  const ZOOM_SCALE = 1.12; // Zoom in 12% to push watermark out of view
  const ZOOM_ORIGIN_X = 0.5; // Center horizontally
  const ZOOM_ORIGIN_Y = 0.3; // Bias toward top (away from watermark)

  // Draw frame to canvas with zoom and cover positioning
  const drawFrameToCanvas = useCallback((frame: ImageBitmap) => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;

    canvas.width = containerWidth;
    canvas.height = containerHeight;

    const frameAspect = frame.width / frame.height;
    const containerAspect = containerWidth / containerHeight;

    // Calculate base dimensions for object-fit: cover
    let drawWidth: number;
    let drawHeight: number;

    if (containerAspect > frameAspect) {
      // Container is wider - fit to width
      drawWidth = containerWidth * ZOOM_SCALE;
      drawHeight = drawWidth / frameAspect;
    } else {
      // Container is taller - fit to height
      drawHeight = containerHeight * ZOOM_SCALE;
      drawWidth = drawHeight * frameAspect;
    }

    // Position with zoom origin offset
    const drawX = (containerWidth - drawWidth) * ZOOM_ORIGIN_X;
    const drawY = (containerHeight - drawHeight) * ZOOM_ORIGIN_Y;

    // Clear and draw with black-to-transparent filter
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw the frame
    ctx.drawImage(frame, drawX, drawY, drawWidth, drawHeight);

    // Apply edge feathering to blend black edges
    applyEdgeFeathering(ctx, containerWidth, containerHeight);
  }, []);

  // Feather edges to blend black borders with page background
  const applyEdgeFeathering = (
    ctx: CanvasRenderingContext2D,
    width: number,
    height: number
  ) => {
    const featherSize = 60;
    const pageBackground = '#0B0F14'; // Match aurora-bg

    // Top edge gradient
    const topGradient = ctx.createLinearGradient(0, 0, 0, featherSize);
    topGradient.addColorStop(0, pageBackground);
    topGradient.addColorStop(1, 'transparent');
    ctx.fillStyle = topGradient;
    ctx.fillRect(0, 0, width, featherSize);

    // Bottom edge gradient (stronger to hide watermark area)
    const bottomGradient = ctx.createLinearGradient(0, height - featherSize * 2, 0, height);
    bottomGradient.addColorStop(0, 'transparent');
    bottomGradient.addColorStop(0.5, `${pageBackground}88`);
    bottomGradient.addColorStop(1, pageBackground);
    ctx.fillStyle = bottomGradient;
    ctx.fillRect(0, height - featherSize * 2, width, featherSize * 2);

    // Left edge
    const leftGradient = ctx.createLinearGradient(0, 0, featherSize, 0);
    leftGradient.addColorStop(0, pageBackground);
    leftGradient.addColorStop(1, 'transparent');
    ctx.fillStyle = leftGradient;
    ctx.fillRect(0, 0, featherSize, height);

    // Right edge
    const rightGradient = ctx.createLinearGradient(width - featherSize, 0, width, 0);
    rightGradient.addColorStop(0, 'transparent');
    rightGradient.addColorStop(1, pageBackground);
    ctx.fillStyle = rightGradient;
    ctx.fillRect(width - featherSize, 0, featherSize, height);
  };

  // Extract frames for scroll control
  const extractFrames = useCallback(async () => {
    const video = videoRef.current;
    if (!video) return;

    if (video.readyState < 1) {
      await new Promise<void>((resolve) => {
        video.addEventListener('loadedmetadata', () => resolve(), { once: true });
      });
    }

    const duration = video.duration;
    const frameCount = 60; // 60 frames for smooth scrubbing
    const frames: ImageBitmap[] = [];

    const offscreenCanvas = document.createElement('canvas');
    offscreenCanvas.width = video.videoWidth || 1280;
    offscreenCanvas.height = video.videoHeight || 720;
    const offCtx = offscreenCanvas.getContext('2d');
    if (!offCtx) return;

    for (let i = 0; i < frameCount; i++) {
      const time = (i / frameCount) * duration;
      video.currentTime = time;

      await new Promise<void>((resolve) => {
        const handleSeeked = () => {
          video.removeEventListener('seeked', handleSeeked);
          resolve();
        };
        video.addEventListener('seeked', handleSeeked);
      });

      offCtx.drawImage(video, 0, 0, offscreenCanvas.width, offscreenCanvas.height);
      try {
        const bitmap = await createImageBitmap(offscreenCanvas);
        frames.push(bitmap);
      } catch (error) {
        console.error('Failed to create bitmap for frame', i, error);
      }
    }

    framesRef.current = frames;

    // Draw first frame (video at start position)
    if (frames.length > 0) {
      drawFrameToCanvas(frames[0]);
    }

    setFramesReady(true);
  }, [drawFrameToCanvas]);

  // Handle image load
  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  // Video event handlers
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !imageLoaded) return;

    const handleCanPlay = () => {
      setVideoReady(true);
      // Start playing once image has loaded
      video.play()
        .then(() => {
          setVideoPlaying(true);
          onVideoReady?.();
        })
        .catch(() => {
          // Autoplay blocked - extract frames immediately
          extractFrames();
        });
    };

    const handleEnded = () => {
      setVideoPlaying(false);
      extractFrames();
    };

    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('ended', handleEnded);

    return () => {
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('ended', handleEnded);
    };
  }, [imageLoaded, extractFrames, onVideoReady]);

  // Scroll-controlled frame display
  useEffect(() => {
    if (!framesReady || framesRef.current.length === 0) return;

    const handleScroll = () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      animationFrameRef.current = requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        // Map scroll position to frame index
        // Use first 1500px of scroll for full video scrub
        const maxScroll = 1500;
        const scrollProgress = Math.min(Math.max(scrollY / maxScroll, 0), 1);

        const frameIndex = Math.min(
          Math.floor(scrollProgress * framesRef.current.length),
          framesRef.current.length - 1
        );
        const frame = framesRef.current[frameIndex];

        if (frame) {
          drawFrameToCanvas(frame);
        }
      });
    };

    const handleResize = () => {
      // Redraw current frame at new dimensions
      const scrollY = window.scrollY;
      const maxScroll = 1500;
      const scrollProgress = Math.min(Math.max(scrollY / maxScroll, 0), 1);
      const frameIndex = Math.min(
        Math.floor(scrollProgress * framesRef.current.length),
        framesRef.current.length - 1
      );
      const frame = framesRef.current[frameIndex];
      if (frame) {
        drawFrameToCanvas(frame);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleResize);

    // Initial draw
    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [framesReady, drawFrameToCanvas]);

  return (
    <div
      ref={containerRef}
      className="hero-video-container"
    >
      {/* Hero image - visible until video plays */}
      <Image
        src="/hero-img2.png"
        alt="Janus riding an iridescent bull"
        fill
        priority
        sizes="100vw"
        className="hero-video-poster"
        style={{
          opacity: videoPlaying || framesReady ? 0 : 1,
          zIndex: 1,
        }}
        onLoad={handleImageLoad}
      />

      {/* Video element - visible while playing */}
      <video
        ref={videoRef}
        muted
        playsInline
        preload="metadata"
        className="hero-video-element"
        style={{
          opacity: videoPlaying && !framesReady ? 1 : 0,
          zIndex: videoPlaying && !framesReady ? 2 : 0,
        }}
      >
        <source src="/Janus_God_and_Bull_Video_Generation.mp4" type="video/mp4" />
      </video>

      {/* Canvas for scroll-controlled frames */}
      <canvas
        ref={canvasRef}
        className="hero-video-canvas"
        style={{
          opacity: framesReady ? 1 : 0,
          zIndex: framesReady ? 2 : 0,
        }}
      />

      {/* Watermark cover overlay - positioned over bottom-right */}
      <div className="hero-video-watermark-cover" />

      {/* Edge glow effects */}
      <div className="hero-video-glow" />
      <div className="hero-video-rim" />
    </div>
  );
}
```

### FR-2: CSS Styling for In-Place Video

```css
/* ui/src/app/globals.css */

/* ─── Hero Video Container ──────────────────────────────────────────────────── */

.hero-video-container {
  position: relative;
  width: 100%;
  height: clamp(320px, 58vh, 760px);
  overflow: hidden;
  background: transparent;
}

.hero-video-poster {
  object-fit: cover;
  object-position: center 20%;
  filter: saturate(1.1) contrast(1.05);
  transition: opacity 0.5s ease-out;
}

.hero-video-element {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 30%; /* Bias toward top to push watermark down */
  transform: scale(1.12); /* Zoom to hide watermark */
  transform-origin: center 30%;
  transition: opacity 0.5s ease-out;
}

.hero-video-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  transition: opacity 0.5s ease-out;
}

/* Watermark cover - black box over bottom-right corner */
.hero-video-watermark-cover {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 120px;
  height: 40px;
  background: linear-gradient(
    135deg,
    transparent 0%,
    rgba(11, 15, 20, 0.8) 40%,
    #0B0F14 100%
  );
  pointer-events: none;
  z-index: 3;
}

/* Glow overlay matching hero-image-glow */
.hero-video-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(
      ellipse 60% 50% at 20% 15%,
      rgba(99, 210, 151, 0.22) 0%,
      transparent 55%
    ),
    radial-gradient(
      ellipse 70% 60% at 85% 75%,
      rgba(139, 92, 246, 0.24) 0%,
      transparent 60%
    );
  opacity: 0.7;
  mix-blend-mode: screen;
  pointer-events: none;
  z-index: 4;
}

/* Rim/vignette effect */
.hero-video-rim {
  position: absolute;
  inset: 0;
  box-shadow:
    inset 0 0 80px rgba(5, 7, 9, 0.75),
    inset 0 0 200px rgba(5, 7, 9, 0.55);
  pointer-events: none;
  z-index: 5;
}

/* Border at bottom */
.hero-video-container::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(31, 41, 55, 0.7);
  z-index: 6;
}
```

### FR-3: Update HeroSection Component

```tsx
// ui/src/components/landing/HeroSection.tsx

'use client';

import Link from 'next/link';
import { HeroVideo } from './HeroVideo';

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />

      {/* In-place hero video (replaces hero-image-stage) */}
      <HeroVideo />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 pt-12 lg:pt-20 text-center">
        <div data-reveal className="reveal">
          <p className="hero-kicker">The Open Intelligence Rodeo</p>
          <h1 className="hero-title">
            <span className="gradient-text">JANUS</span>
          </h1>
          <p className="hero-subtitle">
            Anything In. Anything Out. Build the intelligence engine for the decentralized
            intelligence network powered by Bittensor.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/chat" className="btn-primary text-base px-8 py-3">
              Janus Chat
            </Link>
            <Link href="/competition" className="btn-secondary text-base px-8 py-3">
              Join the Competition
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
```

### FR-4: Video Post-Processing with FFmpeg (Optional Enhancement)

If CSS solutions aren't sufficient, post-process the video with ffmpeg:

```bash
#!/bin/bash
# scripts/process-hero-video.sh

INPUT="ui/public/Janus_God_and_Bull_Video_Generation.mp4"
OUTPUT="ui/public/hero-video-processed.mp4"

# Options:
# 1. Crop to remove watermark (loses some frame)
# 2. Zoom/scale to push watermark out of view
# 3. Overlay black box on watermark region
# 4. Replace near-black pixels with transparency (requires WebM)

# Option 1: Zoom and crop (12% zoom, centered toward top)
ffmpeg -i "$INPUT" \
  -vf "scale=1.12*iw:1.12*ih,crop=iw/1.12:ih/1.12:0.06*iw:0" \
  -c:v libx264 -preset slow -crf 18 \
  -an \
  "$OUTPUT"

# Option 2: Add black overlay on watermark region
# ffmpeg -i "$INPUT" \
#   -vf "drawbox=x=iw-150:y=ih-50:w=150:h=50:color=black:t=fill" \
#   -c:v libx264 -preset slow -crf 18 \
#   -an \
#   "$OUTPUT"

# Option 3: Create WebM with alpha channel (requires chroma key on black)
# Note: Only works if video has pure black background
# ffmpeg -i "$INPUT" \
#   -vf "colorkey=black:0.1:0.1,format=yuva420p" \
#   -c:v libvpx-vp9 -crf 30 -b:v 0 \
#   -an \
#   "ui/public/hero-video-alpha.webm"

echo "Processed video saved to $OUTPUT"
```

### FR-5: Transparent Background Handling

For proper transparency support, convert to WebM with alpha:

```bash
# Create WebM with alpha channel for black background removal
# This requires the video to have consistent black backgrounds

ffmpeg -i ui/public/Janus_God_and_Bull_Video_Generation.mp4 \
  -vf "chromakey=0x000000:0.15:0.1,format=yuva420p" \
  -c:v libvpx-vp9 \
  -pix_fmt yuva420p \
  -crf 30 -b:v 2M \
  -an \
  ui/public/hero-video-alpha.webm
```

Update component to prefer WebM with fallback:

```tsx
<video ref={videoRef} muted playsInline preload="metadata" className="hero-video-element">
  <source src="/hero-video-alpha.webm" type="video/webm" />
  <source src="/Janus_God_and_Bull_Video_Generation.mp4" type="video/mp4" />
</video>
```

### FR-6: Cleanup Old Modal Component

Delete or deprecate the old modal component:

```bash
# Remove old modal implementation
rm ui/src/components/landing/HeroVideoModal.tsx

# Update exports
# ui/src/components/landing/index.ts - remove HeroVideoModal export
```

## Testing Requirements

### Visual Testing with Playwright

```typescript
// tests/visual/test_hero_video.ts

import { test, expect } from '@playwright/test';

const viewports = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 812 },
];

test.describe('Hero Video', () => {
  for (const viewport of viewports) {
    test(`renders correctly on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('http://localhost:3000');

      // Wait for hero image to load
      await page.waitForSelector('.hero-video-poster');
      await page.waitForLoadState('networkidle');

      // Screenshot of initial state (image visible)
      await page.screenshot({
        path: `test-screenshots/hero-initial-${viewport.name}.png`,
        fullPage: false,
      });

      // Wait for video to start (up to 5 seconds)
      await page.waitForTimeout(2000);

      // Screenshot during video playback
      await page.screenshot({
        path: `test-screenshots/hero-video-playing-${viewport.name}.png`,
      });

      // Wait for video to end and frames to be ready
      await page.waitForTimeout(10000);

      // Screenshot after video (canvas mode)
      await page.screenshot({
        path: `test-screenshots/hero-video-ended-${viewport.name}.png`,
      });

      // Test scroll behavior
      await page.evaluate(() => window.scrollTo(0, 500));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `test-screenshots/hero-scroll-500-${viewport.name}.png`,
      });

      await page.evaluate(() => window.scrollTo(0, 1000));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `test-screenshots/hero-scroll-1000-${viewport.name}.png`,
      });

      await page.evaluate(() => window.scrollTo(0, 1500));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: `test-screenshots/hero-scroll-1500-${viewport.name}.png`,
      });
    });

    test(`video-image alignment on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('http://localhost:3000');

      // Get hero image bounds
      const imageBox = await page.locator('.hero-video-poster').boundingBox();

      // Wait for video
      await page.waitForTimeout(3000);

      // Get video/canvas bounds
      const videoBox = await page.locator('.hero-video-element, .hero-video-canvas').first().boundingBox();

      // Verify alignment (allowing small tolerance)
      if (imageBox && videoBox) {
        expect(Math.abs(imageBox.x - videoBox.x)).toBeLessThan(5);
        expect(Math.abs(imageBox.y - videoBox.y)).toBeLessThan(5);
        expect(Math.abs(imageBox.width - videoBox.width)).toBeLessThan(10);
        expect(Math.abs(imageBox.height - videoBox.height)).toBeLessThan(10);
      }
    });

    test(`watermark not visible on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('http://localhost:3000');

      // Wait for video to play
      await page.waitForTimeout(5000);

      // Take screenshot and visually verify no VEO text visible
      // (Manual verification or OCR-based check)
      await page.screenshot({
        path: `test-screenshots/hero-watermark-check-${viewport.name}.png`,
      });
    });
  }

  test('video plays without audio', async ({ page }) => {
    await page.goto('http://localhost:3000');

    // Check video element has muted attribute
    const video = page.locator('.hero-video-element');
    await expect(video).toHaveAttribute('muted', '');

    // Verify no audio plays (can't directly test, but ensure muted)
    const isMuted = await video.evaluate((el: HTMLVideoElement) => el.muted);
    expect(isMuted).toBe(true);
  });

  test('no console errors during video playback', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('http://localhost:3000');
    await page.waitForTimeout(12000); // Full video duration + buffer

    // Filter out expected/benign errors
    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('autoplay')
    );

    expect(significantErrors).toHaveLength(0);
  });
});
```

## Acceptance Criteria

- [ ] Video auto-plays when hero image has loaded
- [ ] Video plays in-place (no modal)
- [ ] First video frame perfectly aligns with hero image position
- [ ] No visible jump or resize when transitioning image → video
- [ ] VEO watermark not visible (zoomed out or covered)
- [ ] Black background blends with page (feathered edges or transparency)
- [ ] After video ends, scroll controls frame scrubbing
- [ ] Scroll up/down smoothly scrubs through video frames
- [ ] Audio is muted
- [ ] Works on desktop (1920x1080)
- [ ] Works on tablet (768x1024)
- [ ] Works on mobile (375x812)
- [ ] No console errors during playback
- [ ] Graceful fallback if autoplay blocked (extract frames immediately)

## Files to Modify

```
ui/
├── src/
│   ├── app/
│   │   └── globals.css                    # Add hero-video styles
│   └── components/
│       └── landing/
│           ├── HeroSection.tsx            # Use new HeroVideo
│           ├── HeroVideo.tsx              # NEW: In-place video component
│           ├── HeroVideoModal.tsx         # DELETE: Old modal
│           └── index.ts                   # Update exports
├── public/
│   ├── Janus_God_and_Bull_Video_Generation.mp4  # Original
│   └── hero-video-processed.mp4           # Optional: Post-processed

scripts/
└── process-hero-video.sh                  # FFmpeg processing script

tests/
└── visual/
    └── test_hero_video.ts                 # Playwright visual tests
```

## Related Specs

- `specs/18_landing_page.md` - Landing page design
- `specs/22_ui_polish.md` - UI styling guidelines
- `specs/29_hero_video_easter_egg.md` - Original easter egg implementation (superseded)

## References

- chutes-frontend HeroVideo implementation: `/home/flori/Dev/chutes/chutes-frontend/src/components/sections/HeroVideo.tsx`
- Scroll-controlled video frame scrubbing pattern
- Canvas-based frame rendering for smooth performance
