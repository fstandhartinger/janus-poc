'use client';

import { useEffect, useState } from 'react';
import type {
  AudioContent,
  FileContent,
  ImageUrlContent,
  MessageContent,
  VideoContent,
} from '@/types/chat';
import { detectFileCategoryFromMetadata, formatBytes } from '@/lib/file-utils';
import { AudioPlayer } from './AudioPlayer';
import { FileIcon } from './FileIcon';

type MediaItem = ImageUrlContent | VideoContent | AudioContent | FileContent;

interface MediaRendererProps {
  content: MessageContent | null | undefined;
}

const MAX_IMAGE_BYTES = 1_000_000;
const MAX_IMAGE_DIMENSION = 1600;

export function MediaRenderer({ content }: MediaRendererProps) {
  if (!content || typeof content === 'string') {
    return null;
  }

  const mediaItems = content.filter(
    (item): item is MediaItem =>
      item.type === 'image_url' || item.type === 'video' || item.type === 'audio' || item.type === 'file'
  );

  if (mediaItems.length === 0) {
    return null;
  }

  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {mediaItems.map((item, index) => (
        <MediaItemView key={`${item.type}-${index}`} item={item} />
      ))}
    </div>
  );
}

function MediaItemView({ item }: { item: MediaItem }) {
  switch (item.type) {
    case 'image_url':
      return <ImageDisplay url={item.image_url.url} />;
    case 'video':
      return <VideoPlayer video={item.video} />;
    case 'audio':
      return (
        <AudioPlayer
          src={item.audio.url}
          title="Audio clip"
          downloadName={getAudioDownloadName(item.audio)}
        />
      );
    case 'file':
      return <FileDownload file={item.file} />;
    default:
      return null;
  }
}

function ImageDisplay({ url }: { url: string }) {
  const [expanded, setExpanded] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const displayUrl = useCompressedImage(url);

  useEffect(() => {
    setLoaded(false);
  }, [displayUrl]);

  useEffect(() => {
    if (!expanded) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setExpanded(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [expanded]);

  return (
    <>
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="relative max-w-[300px] max-h-[300px] rounded-lg border border-[#1F2937] overflow-hidden focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#63D297]"
        aria-label="Expand image"
      >
        {!loaded && <div className="absolute inset-0 animate-pulse bg-[#111726]" aria-hidden="true" />}
        <img
          src={displayUrl}
          alt="Attached"
          loading="lazy"
          decoding="async"
          onLoad={() => setLoaded(true)}
          className={`block max-w-[300px] max-h-[300px] object-cover transition-opacity ${
            loaded ? 'opacity-100' : 'opacity-0'
          }`}
        />
      </button>

      {expanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setExpanded(false)}
          role="dialog"
          aria-modal="true"
          aria-label="Expanded image preview"
        >
          <button
            type="button"
            onClick={() => setExpanded(false)}
            className="absolute top-4 right-4 rounded-full border border-white/20 px-3 py-1 text-xs text-white uppercase tracking-[0.2em]"
            aria-label="Close image preview"
          >
            Close
          </button>
          <img
            src={displayUrl}
            alt="Expanded"
            className="max-w-full max-h-full object-contain rounded-lg"
            onClick={(event) => event.stopPropagation()}
          />
        </div>
      )}
    </>
  );
}

function VideoPlayer({ video }: { video: VideoContent['video'] }) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div className="relative max-w-[420px] w-full rounded-lg overflow-hidden border border-[#1F2937] bg-[#0B0F14]">
      {!loaded && <div className="absolute inset-0 animate-pulse bg-[#111726]" aria-hidden="true" />}
      <video
        src={video.url}
        poster={video.poster}
        controls
        playsInline
        preload="metadata"
        onLoadedMetadata={() => setLoaded(true)}
        className={`w-full transition-opacity ${loaded ? 'opacity-100' : 'opacity-0'}`}
      >
        <source src={video.url} />
        Your browser does not support video playback.
      </video>
    </div>
  );
}

function getAudioDownloadName(audio: AudioContent['audio']) {
  const mimeType = audio.mime_type || '';
  if (mimeType.includes('mpeg') || mimeType.includes('mp3')) {
    return 'audio.mp3';
  }
  if (mimeType.includes('ogg')) {
    return 'audio.ogg';
  }
  if (mimeType.includes('wav')) {
    return 'audio.wav';
  }
  return 'audio.wav';
}

function FileDownload({ file }: { file: FileContent['file'] }) {
  const [downloadUrl, setDownloadUrl] = useState<string | null>(file.url ?? null);
  const mimeType = file.mime_type || '';
  const category = detectFileCategoryFromMetadata(file.name, mimeType) || 'text';
  const sizeLabel = file.size ? formatBytes(file.size) : mimeType || 'File';

  useEffect(() => {
    if (file.url) {
      setDownloadUrl(file.url);
      return;
    }

    if (!file.content) {
      setDownloadUrl(null);
      return;
    }

    if (file.content.startsWith('data:')) {
      setDownloadUrl(file.content);
      return;
    }

    const base64Url = buildBase64Url(file.content, mimeType);
    if (base64Url) {
      setDownloadUrl(base64Url);
      return;
    }

    const blob = new Blob([file.content], { type: mimeType || 'text/plain' });
    const objectUrl = URL.createObjectURL(blob);
    setDownloadUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file.content, file.url, mimeType]);

  const fileLabel = file.name || 'Download file';
  const FileVisual = mimeType.startsWith('video/')
    ? FilmIcon
    : mimeType.startsWith('audio/')
      ? MusicIcon
      : null;

  const content = (
    <>
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#1F2937] text-[#9CA3AF]">
        {FileVisual ? <FileVisual className="h-5 w-5" /> : <FileIcon category={category} className="h-5 w-5" />}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#E5E7EB] truncate">{fileLabel}</p>
        <p className="text-xs text-[#6B7280]">{sizeLabel}</p>
      </div>
      <DownloadIcon className="h-4 w-4 text-[#9CA3AF]" />
    </>
  );

  if (!downloadUrl) {
    return (
      <div className="flex items-center gap-3 p-3 rounded-lg bg-[#0F172A]/70 border border-[#1F2937]">
        {content}
      </div>
    );
  }

  return (
    <a
      href={downloadUrl}
      download={file.name}
      className="flex items-center gap-3 p-3 rounded-lg bg-[#0F172A]/70 border border-[#1F2937] hover:bg-[#111827]/70 transition-colors"
      aria-label={`Download ${fileLabel}`}
    >
      {content}
    </a>
  );
}

function buildBase64Url(content: string, mimeType?: string) {
  const trimmed = content.trim();
  if (!trimmed) return null;
  const base64Pattern = /^[A-Za-z0-9+/]+={0,2}$/;
  if (trimmed.length % 4 !== 0 || !base64Pattern.test(trimmed)) {
    return null;
  }
  const safeMime = mimeType || 'application/octet-stream';
  return `data:${safeMime};base64,${trimmed}`;
}

function estimateDataUrlSize(dataUrl: string) {
  const commaIndex = dataUrl.indexOf(',');
  if (commaIndex === -1) return 0;
  const base64 = dataUrl.slice(commaIndex + 1);
  if (!base64) return 0;
  return Math.ceil((base64.length * 3) / 4);
}

function getDataUrlMimeType(dataUrl: string) {
  const match = /^data:([^;]+);/i.exec(dataUrl);
  return match?.[1] || '';
}

function useCompressedImage(url: string) {
  const [displayUrl, setDisplayUrl] = useState(url);

  useEffect(() => {
    let cancelled = false;
    setDisplayUrl(url);

    if (!url.startsWith('data:image/')) {
      return;
    }

    const size = estimateDataUrlSize(url);
    if (size <= MAX_IMAGE_BYTES) {
      return;
    }

    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const scale = Math.min(1, MAX_IMAGE_DIMENSION / Math.max(image.width, image.height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.width * scale));
      canvas.height = Math.max(1, Math.round(image.height * scale));
      const context = canvas.getContext('2d');
      if (!context) {
        setDisplayUrl(url);
        return;
      }
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const sourceMime = getDataUrlMimeType(url);
      const targetMime = sourceMime === 'image/png' ? 'image/png' : 'image/jpeg';
      const compressed =
        targetMime === 'image/jpeg'
          ? canvas.toDataURL(targetMime, 0.82)
          : canvas.toDataURL(targetMime);
      const compressedSize = estimateDataUrlSize(compressed);
      setDisplayUrl(compressedSize && compressedSize < size ? compressed : url);
    };
    image.onerror = () => {
      if (!cancelled) {
        setDisplayUrl(url);
      }
    };
    image.src = url;

    return () => {
      cancelled = true;
    };
  }, [url]);

  return displayUrl;
}

function MusicIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M9 18a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" />
      <path d="M15 16a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" />
      <path d="M9 18V5l10-2v13" />
    </svg>
  );
}

function FilmIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="2" y="5" width="20" height="14" rx="2" />
      <path d="M8 5v14M16 5v14M2 9h6M2 15h6M16 9h6M16 15h6" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M4 21h16" />
    </svg>
  );
}
