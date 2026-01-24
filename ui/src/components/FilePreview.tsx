import type { AttachedFile } from '@/lib/file-types';
import { formatBytes } from '@/lib/file-utils';
import { FileIcon } from './FileIcon';

interface FilePreviewProps {
  file: AttachedFile;
  onRemove: () => void;
  disabled?: boolean;
}

export function FilePreview({ file, onRemove, disabled }: FilePreviewProps) {
  const isImage = file.category === 'images';

  return (
    <div className="group relative flex items-center gap-2 rounded-lg border border-[#1F2937] bg-[#0F172A]/70 p-2 max-w-[220px]">
      {isImage ? (
        <img
          src={file.content}
          alt={file.name}
          className="h-10 w-10 rounded object-cover"
        />
      ) : (
        <div className="flex h-10 w-10 items-center justify-center rounded bg-[#1F2937] text-[#9CA3AF]">
          <FileIcon category={file.category} className="h-5 w-5" />
        </div>
      )}

      <div className="flex-1 min-w-0">
        <p className="truncate text-xs font-medium text-[#E5E7EB]">{file.name}</p>
        <p className="text-xs text-[#6B7280]">{formatBytes(file.size)}</p>
      </div>

      {!disabled && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute -right-2 -top-2 rounded-full bg-[#1F2937] p-1 text-[#9CA3AF] opacity-0 transition-opacity group-hover:opacity-100 hover:bg-[#FA5D19]/20 hover:text-[#FA5D19]"
          aria-label={`Remove ${file.name}`}
        >
          <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth="1.6">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  );
}
