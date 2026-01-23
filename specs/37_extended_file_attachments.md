# Spec 37: Extended File Attachment Support

## Status: DRAFT

## Context / Why

The current chat UI only supports image attachments (`accept="image/*"`). Users frequently need to share documents for analysis, code review, or data processing. Supporting additional file formats enables richer interactions:

- **PDFs** - Academic papers, contracts, documentation
- **Office documents** - Reports, spreadsheets, presentations
- **Text files** - Code, logs, configuration files
- **Data files** - CSV, JSON, XML for analysis

The baseline implementations need to extract content from these files and include it in the context sent to the LLM.

## Goals

- Expand file attachment support beyond images
- Support common document formats (PDF, DOCX, XLSX, PPTX)
- Support text-based formats (TXT, MD, CSV, JSON, XML, YAML)
- Support code files with syntax detection
- Provide file preview in chat UI
- Extract text content for LLM context

## Non-Goals

- Real-time collaborative editing
- File storage/cloud sync
- OCR for scanned documents (future enhancement)
- Editing attached files

## Functional Requirements

### FR-1: Supported File Types

```typescript
// ui/src/lib/file-types.ts

export const SUPPORTED_FILE_TYPES = {
  // Images (existing)
  images: {
    extensions: ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'],
    mimeTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'],
    maxSize: 10 * 1024 * 1024, // 10MB
    icon: 'ImageIcon',
  },

  // Documents
  pdf: {
    extensions: ['.pdf'],
    mimeTypes: ['application/pdf'],
    maxSize: 50 * 1024 * 1024, // 50MB
    icon: 'FileTextIcon',
  },
  word: {
    extensions: ['.docx', '.doc'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'
    ],
    maxSize: 25 * 1024 * 1024, // 25MB
    icon: 'FileTextIcon',
  },
  excel: {
    extensions: ['.xlsx', '.xls', '.csv'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'text/csv'
    ],
    maxSize: 25 * 1024 * 1024, // 25MB
    icon: 'TableIcon',
  },
  powerpoint: {
    extensions: ['.pptx', '.ppt'],
    mimeTypes: [
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      'application/vnd.ms-powerpoint'
    ],
    maxSize: 50 * 1024 * 1024, // 50MB
    icon: 'PresentationIcon',
  },

  // Text/Code
  text: {
    extensions: ['.txt', '.md', '.markdown', '.rst'],
    mimeTypes: ['text/plain', 'text/markdown', 'text/x-rst'],
    maxSize: 5 * 1024 * 1024, // 5MB
    icon: 'FileIcon',
  },
  code: {
    extensions: [
      '.js', '.ts', '.jsx', '.tsx', '.py', '.rb', '.go', '.rs',
      '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.swift',
      '.kt', '.scala', '.sh', '.bash', '.zsh', '.ps1', '.sql'
    ],
    mimeTypes: ['text/javascript', 'text/typescript', 'text/x-python', 'text/x-java-source'],
    maxSize: 2 * 1024 * 1024, // 2MB
    icon: 'CodeIcon',
  },
  data: {
    extensions: ['.json', '.xml', '.yaml', '.yml', '.toml'],
    mimeTypes: ['application/json', 'application/xml', 'text/yaml', 'application/toml'],
    maxSize: 10 * 1024 * 1024, // 10MB
    icon: 'DatabaseIcon',
  },
} as const;

export const ALL_ACCEPT_TYPES = Object.values(SUPPORTED_FILE_TYPES)
  .flatMap(t => [...t.extensions, ...t.mimeTypes])
  .join(',');

export const MAX_FILES_PER_MESSAGE = 10;
export const MAX_TOTAL_SIZE = 100 * 1024 * 1024; // 100MB total
```

### FR-2: Updated File Input Component

```typescript
// ui/src/components/ChatInput.tsx

import { SUPPORTED_FILE_TYPES, ALL_ACCEPT_TYPES, MAX_FILES_PER_MESSAGE } from '@/lib/file-types';

export interface AttachedFile {
  id: string;
  name: string;
  type: string;
  size: number;
  category: keyof typeof SUPPORTED_FILE_TYPES;
  // For images: data URL
  // For documents: extracted text content
  content: string;
  // Original file for re-upload if needed
  file?: File;
  // Preview data (first N chars for text, thumbnail for images)
  preview?: string;
}

const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const files = Array.from(e.target.files || []);

  if (attachedFiles.length + files.length > MAX_FILES_PER_MESSAGE) {
    toast.error(`Maximum ${MAX_FILES_PER_MESSAGE} files per message`);
    return;
  }

  for (const file of files) {
    const category = detectFileCategory(file);
    if (!category) {
      toast.error(`Unsupported file type: ${file.name}`);
      continue;
    }

    const typeConfig = SUPPORTED_FILE_TYPES[category];
    if (file.size > typeConfig.maxSize) {
      toast.error(`${file.name} exceeds ${formatBytes(typeConfig.maxSize)} limit`);
      continue;
    }

    try {
      const processed = await processFile(file, category);
      setAttachedFiles(prev => [...prev, processed]);
    } catch (error) {
      toast.error(`Failed to process ${file.name}`);
    }
  }

  // Reset input
  e.target.value = '';
};
```

### FR-3: File Processing Service

```typescript
// ui/src/lib/file-processor.ts

import * as pdfjs from 'pdfjs-dist';
import mammoth from 'mammoth';
import * as XLSX from 'xlsx';

export async function processFile(
  file: File,
  category: string
): Promise<AttachedFile> {
  const id = crypto.randomUUID();

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
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string;
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
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function processPDF(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;

  let fullText = '';
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const textContent = await page.getTextContent();
    const pageText = textContent.items
      .map((item: any) => item.str)
      .join(' ');
    fullText += `\n--- Page ${i} ---\n${pageText}`;
  }

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'pdf',
    content: fullText.trim(),
    preview: fullText.slice(0, 500) + (fullText.length > 500 ? '...' : ''),
  };
}

async function processWord(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  const text = result.value;

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'word',
    content: text,
    preview: text.slice(0, 500) + (text.length > 500 ? '...' : ''),
  };
}

async function processExcel(file: File, id: string): Promise<AttachedFile> {
  const arrayBuffer = await file.arrayBuffer();
  const workbook = XLSX.read(arrayBuffer);

  let content = '';
  for (const sheetName of workbook.SheetNames) {
    const sheet = workbook.Sheets[sheetName];
    const csv = XLSX.utils.sheet_to_csv(sheet);
    content += `\n--- Sheet: ${sheetName} ---\n${csv}`;
  }

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'excel',
    content: content.trim(),
    preview: content.slice(0, 500) + (content.length > 500 ? '...' : ''),
  };
}

async function processPowerPoint(file: File, id: string): Promise<AttachedFile> {
  // PowerPoint extraction is complex; use server-side processing
  // For now, upload file and let backend handle extraction
  const base64 = await fileToBase64(file);

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: 'powerpoint',
    content: base64, // Send as base64 for server processing
    preview: `PowerPoint: ${file.name} (${formatBytes(file.size)})`,
    file,
  };
}

async function processText(
  file: File,
  id: string,
  category: string
): Promise<AttachedFile> {
  const text = await file.text();
  const extension = file.name.split('.').pop()?.toLowerCase() || '';

  return {
    id,
    name: file.name,
    type: file.type,
    size: file.size,
    category: category as keyof typeof SUPPORTED_FILE_TYPES,
    content: text,
    preview: text.slice(0, 500) + (text.length > 500 ? '...' : ''),
  };
}
```

### FR-4: File Preview Component

```tsx
// ui/src/components/FilePreview.tsx

import { AttachedFile, SUPPORTED_FILE_TYPES } from '@/lib/file-types';
import { X, FileText, Table, Code, Image, Database, Presentation } from 'lucide-react';

interface FilePreviewProps {
  file: AttachedFile;
  onRemove: () => void;
  disabled?: boolean;
}

const CATEGORY_ICONS = {
  images: Image,
  pdf: FileText,
  word: FileText,
  excel: Table,
  powerpoint: Presentation,
  text: FileText,
  code: Code,
  data: Database,
};

export function FilePreview({ file, onRemove, disabled }: FilePreviewProps) {
  const Icon = CATEGORY_ICONS[file.category] || FileText;
  const isImage = file.category === 'images';

  return (
    <div className="group relative flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800/50 p-2 max-w-[200px]">
      {isImage ? (
        <img
          src={file.content}
          alt={file.name}
          className="h-10 w-10 rounded object-cover"
        />
      ) : (
        <div className="flex h-10 w-10 items-center justify-center rounded bg-ink-700">
          <Icon className="h-5 w-5 text-ink-400" />
        </div>
      )}

      <div className="flex-1 min-w-0">
        <p className="truncate text-xs font-medium text-ink-200">
          {file.name}
        </p>
        <p className="text-xs text-ink-500">
          {formatBytes(file.size)}
        </p>
      </div>

      {!disabled && (
        <button
          onClick={onRemove}
          className="absolute -right-2 -top-2 rounded-full bg-ink-700 p-1 opacity-0 transition-opacity group-hover:opacity-100 hover:bg-red-500/20"
          aria-label={`Remove ${file.name}`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
```

### FR-5: Message Content with Files

Update message content structure to include files:

```typescript
// ui/src/types/chat.ts

export interface FileContent {
  type: 'file';
  file: {
    name: string;
    mime_type: string;
    content: string; // Extracted text or base64
    size: number;
  };
}

export type MessageContent = string | (TextContent | ImageUrlContent | FileContent)[];
```

### FR-6: Backend File Extraction Service

```python
# gateway/janus_gateway/services/file_extractor.py

import io
import base64
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF for PDF
from docx import Document
import openpyxl
from pptx import Presentation


class FileExtractor:
    """Extract text content from various file formats."""

    MAX_TEXT_LENGTH = 100_000  # 100k chars max per file

    def extract(self, content: str, mime_type: str, filename: str) -> str:
        """
        Extract text from file content.

        Args:
            content: Base64-encoded file content or plain text
            mime_type: MIME type of the file
            filename: Original filename for extension detection

        Returns:
            Extracted text content
        """
        extension = Path(filename).suffix.lower()

        # Text-based files - decode and return
        if mime_type.startswith('text/') or extension in ['.json', '.xml', '.yaml', '.yml']:
            try:
                return base64.b64decode(content).decode('utf-8')[:self.MAX_TEXT_LENGTH]
            except:
                return content[:self.MAX_TEXT_LENGTH]

        # Binary files - decode and extract
        try:
            data = base64.b64decode(content)
        except:
            return f"[Could not decode file: {filename}]"

        if mime_type == 'application/pdf' or extension == '.pdf':
            return self._extract_pdf(data)
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword'
        ] or extension in ['.docx', '.doc']:
            return self._extract_docx(data)
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ] or extension in ['.xlsx', '.xls']:
            return self._extract_xlsx(data)
        elif mime_type in [
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-powerpoint'
        ] or extension in ['.pptx', '.ppt']:
            return self._extract_pptx(data)
        else:
            return f"[Unsupported file format: {filename}]"

    def _extract_pdf(self, data: bytes) -> str:
        """Extract text from PDF."""
        text_parts = []
        with fitz.open(stream=data, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
        return '\n\n'.join(text_parts)[:self.MAX_TEXT_LENGTH]

    def _extract_docx(self, data: bytes) -> str:
        """Extract text from Word document."""
        doc = Document(io.BytesIO(data))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n\n'.join(paragraphs)[:self.MAX_TEXT_LENGTH]

    def _extract_xlsx(self, data: bytes) -> str:
        """Extract text from Excel spreadsheet."""
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
        text_parts = []

        for sheet_name in wb.sheetnames:
            sheet = wb[sheet_name]
            rows = []
            for row in sheet.iter_rows(values_only=True):
                row_text = '\t'.join(str(cell) if cell is not None else '' for cell in row)
                if row_text.strip():
                    rows.append(row_text)
            if rows:
                text_parts.append(f"--- Sheet: {sheet_name} ---\n" + '\n'.join(rows))

        return '\n\n'.join(text_parts)[:self.MAX_TEXT_LENGTH]

    def _extract_pptx(self, data: bytes) -> str:
        """Extract text from PowerPoint presentation."""
        prs = Presentation(io.BytesIO(data))
        text_parts = []

        for i, slide in enumerate(prs.slides):
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_text.append(shape.text)
            if slide_text:
                text_parts.append(f"--- Slide {i+1} ---\n" + '\n'.join(slide_text))

        return '\n\n'.join(text_parts)[:self.MAX_TEXT_LENGTH]
```

### FR-7: Message Preprocessing for Files

```python
# gateway/janus_gateway/services/message_processor.py

from typing import Union
from janus_gateway.models.openai import Message, MessageContent, TextContent, FileContent
from janus_gateway.services.file_extractor import FileExtractor


class MessageProcessor:
    """Process messages to extract file contents and prepare for LLM."""

    def __init__(self):
        self.file_extractor = FileExtractor()

    def process_message(self, message: Message) -> Message:
        """
        Process a message, extracting file contents into text.

        Converts FileContent parts into TextContent with extracted text.
        """
        if isinstance(message.content, str):
            return message

        if not message.content:
            return message

        processed_parts = []

        for part in message.content:
            if isinstance(part, dict) and part.get('type') == 'file':
                # Extract file content
                file_info = part.get('file', {})
                extracted = self.file_extractor.extract(
                    content=file_info.get('content', ''),
                    mime_type=file_info.get('mime_type', ''),
                    filename=file_info.get('name', 'unknown')
                )

                # Convert to text content
                processed_parts.append({
                    'type': 'text',
                    'text': f"\n[Attached file: {file_info.get('name', 'unknown')}]\n{extracted}\n[End of file]\n"
                })
            else:
                processed_parts.append(part)

        return Message(
            role=message.role,
            content=processed_parts,
            name=message.name
        )
```

## Non-Functional Requirements

### NFR-1: Performance

- File processing should complete within 5 seconds for typical documents
- Large files (>10MB) show progress indicator
- Client-side processing preferred to reduce server load
- Lazy loading for file preview libraries

### NFR-2: Security

- Validate file types on both client and server
- Sanitize extracted text content
- No executable file types allowed
- Size limits enforced at all layers

### NFR-3: Accessibility

- Screen reader support for file previews
- Keyboard navigation for file list
- Clear error messages for unsupported files

## Dependencies

### Frontend (npm)

```json
{
  "pdfjs-dist": "^4.0.0",
  "mammoth": "^1.6.0",
  "xlsx": "^0.18.5"
}
```

### Backend (pip)

```
PyMuPDF>=1.23.0
python-docx>=1.1.0
openpyxl>=3.1.2
python-pptx>=0.6.23
```

## Acceptance Criteria

- [ ] File input accepts all supported file types
- [ ] PDFs extracted with page numbers
- [ ] Word documents (.docx) text extracted
- [ ] Excel files (.xlsx) converted to CSV-like format
- [ ] PowerPoint slides text extracted
- [ ] Text/code files read directly
- [ ] File preview shows icon and name
- [ ] Size limits enforced with user feedback
- [ ] Multiple files can be attached
- [ ] Files display in message bubbles
- [ ] Backend extracts content for LLM context
- [ ] Tests for each file type

## Files to Modify/Create

```
ui/
├── src/
│   ├── lib/
│   │   ├── file-types.ts         # NEW - File type definitions
│   │   └── file-processor.ts     # NEW - Client-side processing
│   ├── components/
│   │   ├── ChatInput.tsx         # MODIFY - Extended file handling
│   │   ├── FilePreview.tsx       # NEW - File preview component
│   │   └── MessageBubble.tsx     # MODIFY - Display file attachments
│   └── types/
│       └── chat.ts               # MODIFY - Add FileContent type
│
gateway/
└── janus_gateway/
    └── services/
        ├── file_extractor.py     # NEW - Backend extraction
        └── message_processor.py  # NEW - Message preprocessing
```

## Open Questions

1. **Server-side vs client-side**: Should complex formats (PPTX) be processed client or server?
2. **File storage**: Should files be uploaded to artifact store or sent inline?
3. **Token limits**: How to handle files that exceed context window?
4. **Image extraction**: Should we extract images from PDFs/DOCX for vision models?

## Related Specs

- `specs/11_chat_ui.md` - Original chat UI spec
- `specs/28_chat_ui_improvements.md` - Chat UI enhancements
- `specs/38_multimodal_vision_models.md` - Vision model support
