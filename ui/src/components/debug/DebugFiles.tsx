'use client';

type DebugFilesProps = {
  files: string[];
};

const FileGlyph = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    className={className}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M6 3h7l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
    <path d="M13 3v6h6" />
  </svg>
);

export function DebugFiles({ files }: DebugFilesProps) {
  if (files.length === 0) return null;

  return (
    <div className="chat-debug-files">
      <div className="chat-debug-files-title">Created Files</div>
      <div className="chat-debug-files-list">
        {files.map((file) => (
          <div key={file} className="chat-debug-file-row">
            <FileGlyph className="w-3.5 h-3.5" />
            <span>{file}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
