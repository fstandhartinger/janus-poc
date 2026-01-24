import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface CanvasVersion {
  id: string;
  content: string;
  timestamp: number;
  description: string;
}

export interface CanvasDocument {
  id: string;
  title: string;
  language: string;
  content: string;
  versions: CanvasVersion[];
  currentVersionId: string;
  createdAt: number;
  updatedAt: number;
  readonly: boolean;
}

interface CanvasState {
  documents: Map<string, CanvasDocument>;
  activeDocumentId: string | null;
  isOpen: boolean;

  openCanvas: (doc: CanvasDocument) => void;
  closeCanvas: () => void;
  updateContent: (content: string, description?: string) => void;
  restoreVersion: (versionId: string) => void;
  createDocument: (title: string, language: string, content: string, readonly?: boolean) => string;
  getActiveDocument: () => CanvasDocument | null;
}

type PersistedCanvasState = {
  documents: Array<[string, CanvasDocument]>;
  activeDocumentId: string | null;
  isOpen: boolean;
};

export const useCanvasStore = create<CanvasState>()(
  persist(
    (set, get) => ({
      documents: new Map(),
      activeDocumentId: null,
      isOpen: false,

      openCanvas: (doc) => {
        const documents = new Map(get().documents);
        documents.set(doc.id, doc);
        set({ documents, activeDocumentId: doc.id, isOpen: true });
      },

      closeCanvas: () => {
        set({ isOpen: false });
      },

      updateContent: (content, description = 'Edit') => {
        const { activeDocumentId, documents } = get();
        if (!activeDocumentId) return;

        const doc = documents.get(activeDocumentId);
        if (!doc || doc.readonly) return;
        if (doc.content === content) return;

        const newVersion: CanvasVersion = {
          id: crypto.randomUUID(),
          content,
          timestamp: Date.now(),
          description,
        };

        const updatedDoc: CanvasDocument = {
          ...doc,
          content,
          versions: [...doc.versions, newVersion],
          currentVersionId: newVersion.id,
          updatedAt: Date.now(),
        };

        const newDocuments = new Map(documents);
        newDocuments.set(activeDocumentId, updatedDoc);
        set({ documents: newDocuments });
      },

      restoreVersion: (versionId) => {
        const { activeDocumentId, documents } = get();
        if (!activeDocumentId) return;

        const doc = documents.get(activeDocumentId);
        if (!doc || doc.readonly) return;

        const version = doc.versions.find((item) => item.id === versionId);
        if (!version) return;

        const newVersion: CanvasVersion = {
          id: crypto.randomUUID(),
          content: version.content,
          timestamp: Date.now(),
          description: `Restored from ${new Date(version.timestamp).toLocaleString()}`,
        };

        const updatedDoc: CanvasDocument = {
          ...doc,
          content: version.content,
          versions: [...doc.versions, newVersion],
          currentVersionId: newVersion.id,
          updatedAt: Date.now(),
        };

        const newDocuments = new Map(documents);
        newDocuments.set(activeDocumentId, updatedDoc);
        set({ documents: newDocuments });
      },

      createDocument: (title, language, content, readonly = false) => {
        const id = crypto.randomUUID();
        const initialVersion: CanvasVersion = {
          id: crypto.randomUUID(),
          content,
          timestamp: Date.now(),
          description: 'Initial version',
        };

        const doc: CanvasDocument = {
          id,
          title,
          language,
          content,
          versions: [initialVersion],
          currentVersionId: initialVersion.id,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          readonly,
        };

        const documents = new Map(get().documents);
        documents.set(id, doc);
        set({ documents, activeDocumentId: id, isOpen: true });
        return id;
      },

      getActiveDocument: () => {
        const { activeDocumentId, documents } = get();
        if (!activeDocumentId) return null;
        return documents.get(activeDocumentId) || null;
      },
    }),
    {
      name: 'janus-canvas',
      partialize: (state) => ({
        documents: Array.from(state.documents.entries()),
        activeDocumentId: state.activeDocumentId,
        isOpen: state.isOpen,
      }),
      merge: (persistedState, currentState) => {
        const typedState = persistedState as Partial<PersistedCanvasState>;
        return {
          ...currentState,
          ...typedState,
          documents: new Map(typedState.documents ?? []),
        };
      },
    }
  )
);
