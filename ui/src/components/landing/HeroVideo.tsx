'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Image from 'next/image';

interface HeroVideoProps {
  onVideoReady?: () => void;
}

const FRAME_COUNT = 60;
const MAX_SCROLL = 1500;
const ZOOM_SCALE = 1.12;
const ZOOM_ORIGIN_X = 0.5;
const ZOOM_ORIGIN_Y = 0.3;

export function HeroVideo({ onVideoReady }: HeroVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const framesRef = useRef<ImageBitmap[]>([]);
  const animationFrameRef = useRef<number | null>(null);
  const extractingRef = useRef(false);

  const [imageLoaded, setImageLoaded] = useState(false);
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [framesReady, setFramesReady] = useState(false);

  const applyEdgeFeathering = useCallback(
    (ctx: CanvasRenderingContext2D, width: number, height: number) => {
      const featherSize = 60;
      const pageBackground = '#0B0F14';

      const topGradient = ctx.createLinearGradient(0, 0, 0, featherSize);
      topGradient.addColorStop(0, pageBackground);
      topGradient.addColorStop(1, 'transparent');
      ctx.fillStyle = topGradient;
      ctx.fillRect(0, 0, width, featherSize);

      const bottomGradient = ctx.createLinearGradient(0, height - featherSize * 2, 0, height);
      bottomGradient.addColorStop(0, 'transparent');
      bottomGradient.addColorStop(0.5, `${pageBackground}88`);
      bottomGradient.addColorStop(1, pageBackground);
      ctx.fillStyle = bottomGradient;
      ctx.fillRect(0, height - featherSize * 2, width, featherSize * 2);

      const leftGradient = ctx.createLinearGradient(0, 0, featherSize, 0);
      leftGradient.addColorStop(0, pageBackground);
      leftGradient.addColorStop(1, 'transparent');
      ctx.fillStyle = leftGradient;
      ctx.fillRect(0, 0, featherSize, height);

      const rightGradient = ctx.createLinearGradient(width - featherSize, 0, width, 0);
      rightGradient.addColorStop(0, 'transparent');
      rightGradient.addColorStop(1, pageBackground);
      ctx.fillStyle = rightGradient;
      ctx.fillRect(width - featherSize, 0, featherSize, height);
    },
    []
  );

  const drawFrameToCanvas = useCallback(
    (frame: ImageBitmap) => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const containerWidth = container.clientWidth;
      const containerHeight = container.clientHeight;
      if (!containerWidth || !containerHeight) return;

      canvas.width = containerWidth;
      canvas.height = containerHeight;

      const frameAspect = frame.width / frame.height;
      const containerAspect = containerWidth / containerHeight;

      let drawWidth: number;
      let drawHeight: number;

      if (containerAspect > frameAspect) {
        drawWidth = containerWidth * ZOOM_SCALE;
        drawHeight = drawWidth / frameAspect;
      } else {
        drawHeight = containerHeight * ZOOM_SCALE;
        drawWidth = drawHeight * frameAspect;
      }

      const drawX = (containerWidth - drawWidth) * ZOOM_ORIGIN_X;
      const drawY = (containerHeight - drawHeight) * ZOOM_ORIGIN_Y;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(frame, drawX, drawY, drawWidth, drawHeight);
      applyEdgeFeathering(ctx, containerWidth, containerHeight);
    },
    [applyEdgeFeathering]
  );

  const extractFrames = useCallback(async () => {
    if (extractingRef.current || framesReady) return;
    const video = videoRef.current;
    if (!video) return;

    extractingRef.current = true;
    setFramesReady(false);

    try {
      if (video.readyState < 1) {
        await new Promise<void>((resolve) => {
          video.addEventListener('loadedmetadata', () => resolve(), { once: true });
        });
      }

      const duration = Number.isFinite(video.duration) ? video.duration : 0;
      if (!duration) return;

      video.pause();

      framesRef.current.forEach((frame) => frame.close());
      framesRef.current = [];

      const offscreenCanvas = document.createElement('canvas');
      offscreenCanvas.width = video.videoWidth || 1280;
      offscreenCanvas.height = video.videoHeight || 720;
      const offCtx = offscreenCanvas.getContext('2d');
      if (!offCtx) return;

      const frames: ImageBitmap[] = [];

      for (let i = 0; i < FRAME_COUNT; i += 1) {
        const time = (i / FRAME_COUNT) * duration;
        video.currentTime = time;

        await new Promise<void>((resolve) => {
          video.addEventListener('seeked', () => resolve(), { once: true });
        });

        offCtx.drawImage(video, 0, 0, offscreenCanvas.width, offscreenCanvas.height);

        try {
          const bitmap = await createImageBitmap(offscreenCanvas);
          frames.push(bitmap);
        } catch (_error) {
          // Ignore bitmap failures to avoid noisy console errors during playback.
        }
      }

      framesRef.current = frames;

      if (frames.length > 0) {
        drawFrameToCanvas(frames[0]);
      }

      setFramesReady(true);
    } finally {
      extractingRef.current = false;
    }
  }, [drawFrameToCanvas, framesReady]);

  const handleImageLoad = useCallback(() => {
    setImageLoaded(true);
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !imageLoaded) return;

    let started = false;

    const handleCanPlay = () => {
      if (started) return;
      started = true;
      video
        .play()
        .then(() => {
          setVideoPlaying(true);
          onVideoReady?.();
        })
        .catch(() => {
          extractFrames();
        });
    };

    const handleEnded = () => {
      setVideoPlaying(false);
      extractFrames();
    };

    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('ended', handleEnded);

    if (video.readyState >= 3) {
      handleCanPlay();
    }

    return () => {
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('ended', handleEnded);
    };
  }, [imageLoaded, extractFrames, onVideoReady]);

  useEffect(() => {
    if (!framesReady || framesRef.current.length === 0) return;

    const handleScroll = () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }

      animationFrameRef.current = requestAnimationFrame(() => {
        const scrollY = window.scrollY;
        const scrollProgress = Math.min(Math.max(scrollY / MAX_SCROLL, 0), 1);

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
      const scrollY = window.scrollY;
      const scrollProgress = Math.min(Math.max(scrollY / MAX_SCROLL, 0), 1);
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

    handleScroll();

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleResize);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [framesReady, drawFrameToCanvas]);

  useEffect(() => {
    return () => {
      framesRef.current.forEach((frame) => frame.close());
      framesRef.current = [];
    };
  }, []);

  return (
    <div ref={containerRef} className="hero-video-container">
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

      <canvas
        ref={canvasRef}
        className="hero-video-canvas"
        style={{
          opacity: framesReady ? 1 : 0,
          zIndex: framesReady ? 2 : 0,
        }}
      />

      <div className="hero-video-watermark-cover" />
      <div className="hero-video-glow" />
      <div className="hero-video-rim" />
    </div>
  );
}
