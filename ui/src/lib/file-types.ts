export const SUPPORTED_FILE_TYPES = {
  images: {
    extensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
    mimeTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'],
    maxSize: 10 * 1024 * 1024,
    icon: 'ImageIcon',
  },
  pdf: {
    extensions: ['.pdf'],
    mimeTypes: ['application/pdf'],
    maxSize: 50 * 1024 * 1024,
    icon: 'FileTextIcon',
  },
  word: {
    extensions: ['.docx', '.doc'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword',
    ],
    maxSize: 25 * 1024 * 1024,
    icon: 'FileTextIcon',
  },
  excel: {
    extensions: ['.xlsx', '.xls', '.csv'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'text/csv',
    ],
    maxSize: 25 * 1024 * 1024,
    icon: 'TableIcon',
  },
  powerpoint: {
    extensions: ['.pptx', '.ppt'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint',
    ],
    maxSize: 50 * 1024 * 1024,
    icon: 'PresentationIcon',
  },
  text: {
    extensions: ['.txt', '.md', '.markdown', '.rst'],
    mimeTypes: ['text/plain', 'text/markdown', 'text/x-rst'],
    maxSize: 5 * 1024 * 1024,
    icon: 'FileIcon',
  },
  code: {
    extensions: [
      '.js',
      '.ts',
      '.jsx',
      '.tsx',
      '.py',
      '.rb',
      '.go',
      '.rs',
      '.java',
      '.c',
      '.cpp',
      '.h',
      '.hpp',
      '.cs',
      '.php',
      '.swift',
      '.kt',
      '.scala',
      '.sh',
      '.bash',
      '.zsh',
      '.ps1',
      '.sql',
    ],
    mimeTypes: ['text/javascript', 'text/typescript', 'text/x-python', 'text/x-java-source'],
    maxSize: 2 * 1024 * 1024,
    icon: 'CodeIcon',
  },
  data: {
    extensions: ['.json', '.xml', '.yaml', '.yml', '.toml'],
    mimeTypes: ['application/json', 'application/xml', 'text/yaml', 'application/toml'],
    maxSize: 10 * 1024 * 1024,
    icon: 'DatabaseIcon',
  },
} as const;

export type FileCategory = keyof typeof SUPPORTED_FILE_TYPES;

export interface AttachedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  category: FileCategory;
  content: string;
  file?: File;
  preview?: string;
}

export const ALL_ACCEPT_TYPES = Object.values(SUPPORTED_FILE_TYPES)
  .flatMap((type) => [...type.extensions, ...type.mimeTypes])
  .join(',');

export const MAX_FILES_PER_MESSAGE = 10;
export const MAX_TOTAL_SIZE = 100 * 1024 * 1024;
