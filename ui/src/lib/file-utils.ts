import { SUPPORTED_FILE_TYPES, type FileCategory } from './file-types';

const KB = 1024;
const MB = KB * 1024;

function getExtension(filename: string): string {
  const trimmed = filename.trim().toLowerCase();
  const dotIndex = trimmed.lastIndexOf('.');
  return dotIndex >= 0 ? trimmed.slice(dotIndex) : '';
}

export function formatBytes(bytes: number): string {
  if (bytes >= MB) {
    return `${(bytes / MB).toFixed(1)}MB`;
  }
  if (bytes >= KB) {
    return `${(bytes / KB).toFixed(1)}KB`;
  }
  return `${bytes}B`;
}

export function detectFileCategoryFromMetadata(
  filename: string,
  mimeType: string
): FileCategory | null {
  const extension = getExtension(filename);
  const normalizedMime = mimeType.toLowerCase();

  for (const [category, config] of Object.entries(SUPPORTED_FILE_TYPES)) {
    const matchesExtension = config.extensions.some((ext) => ext === extension);
    const matchesMime = config.mimeTypes.some((type) => type === normalizedMime);
    if (matchesExtension || matchesMime) {
      return category as FileCategory;
    }
  }
  return null;
}

export function detectFileCategory(file: File): FileCategory | null {
  return detectFileCategoryFromMetadata(file.name, file.type || '');
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('Failed to read file'));
        return;
      }
      const base64 = result.split(',')[1] || '';
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error || new Error('Failed to read file'));
    reader.readAsDataURL(file);
  });
}
