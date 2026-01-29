import type { AttachedFile, FileCategory } from './file-types';
import { fileToBase64, formatBytes } from './file-utils';

const PREVIEW_LIMIT = 500;
const CONTENT_LIMIT = 100_000;

function createFileId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `file-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function buildPreview(text: string): string {
  if (text.length <= PREVIEW_LIMIT) {
    return text;
  }
  return `${text.slice(0, PREVIEW_LIMIT)}...`;
}

function trimContent(text: string): string {
  return text.slice(0, CONTENT_LIMIT);
}

export async function processFile(file: File, category: FileCategory): Promise<AttachedFile> {
  const id = createFileId();

  switch (category) {
    case 'images':
      return processImage(file, id);
    case 'pdf':
      return processPDF(file, id);
    case 'word':
      return processWord(file, id);
    case 'excel':
      return processExcel(file, id);
    case 'powerpoint':
      return processPowerPoint(file, id);
    case 'text':
    case 'code':
    case 'data':
      return processText(file, id, category);
    default:
      throw new Error(`Unknown category: ${category}`);
  }
}

async function processImage(file: File, id: string): Promise<AttachedFile> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      resolve({
        id,
        name: file.name,
        type: file.type,
        size: file.size,
        category: 'images',
        content: dataUrl,
        preview: dataUrl,
      });
    };
    reader.onerror = () => reject(reader.error || new Error('Failed to read image'));
    reader.readAsDataURL(file);
  });
}

async function processPDF(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf');
  const pdf = await pdfjs.getDocument({ data: arrayBuffer, disableWorker: true }).promise;

  let fullText = '';
  for (let i = 1; i <= pdf.numPages; i += 1) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items
      .map((item: unknown) =>
        typeof item === 'object' && item && 'str' in item ? String((item as { str: string }).str) : ''
      )
      .join(' ');
    fullText += `\n--- Page ${i} ---\n${pageText}`;
  }

  const content = trimContent(fullText.trim());
  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'pdf',
    content,
    preview: buildPreview(content),
  };
}

async function processWord(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const mammoth = await import('mammoth');
  const result = await mammoth.extractRawText({ arrayBuffer });
  const content = trimContent((result.value || '').trim());

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'word',
    content,
    preview: buildPreview(content),
  };
}

async function processExcel(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const XLSX = await import('xlsx');
  const workbook = XLSX.read(arrayBuffer, { type: 'array' });

  let content = '';
  for (const sheetName of workbook.SheetNames) {
    const sheet = workbook.Sheets[sheetName];
    const csv = XLSX.utils.sheet_to_csv(sheet);
    content += `\n--- Sheet: ${sheetName} ---\n${csv}`;
  }

  const trimmed = trimContent(content.trim());
  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'excel',
    content: trimmed,
    preview: buildPreview(trimmed),
  };
}

async function processPowerPoint(file: File, id: string): Promise<AttachedFile> {
  const base64 = await fileToBase64(file);

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'powerpoint',
    content: base64,
    preview: `PowerPoint: ${file.name} (${formatBytes(file.size)})`,
    file,
  };
}

async function processText(
  file: File,
  id: string,
  category: FileCategory
): Promise<AttachedFile> {
  const text = await file.text();
  const content = trimContent(text);

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category,
    content,
    preview: buildPreview(content),
  };
}
