# Spec 77: Memory Management UI

**Status:** COMPLETE
**Priority:** Medium
**Complexity:** Medium
**Prerequisites:** Spec 72, Spec 73, Spec 74

---

## Overview

Add a subtle but functional memory management interface to the chat frontend. Users should be able to:
1. View all their memories
2. Edit memory captions/content
3. Delete individual memories
4. Enable/disable memory feature globally
5. Clear all memories

The UI should be unobtrusive but discoverable.

---

## Functional Requirements

### FR-1: Memory Settings Panel

Add a memory management panel accessible from the chat header or settings.

**Access Point:** Click the brain icon (memory toggle) to open panel, OR add to settings menu.

**Panel Sections:**
1. **Memory Toggle** - Enable/disable memory feature
2. **Memory List** - Scrollable list of all memories
3. **Actions** - Clear all, export (future)

### FR-2: Memory List Component

Display all user memories in a scrollable list.

```tsx
// components/memory/MemoryList.tsx
interface Memory {
  id: string;
  caption: string;
  full_text: string;
  created_at: string;
}

interface MemoryListProps {
  memories: Memory[];
  onEdit: (id: string, updates: Partial<Memory>) => void;
  onDelete: (id: string) => void;
}

export function MemoryList({ memories, onEdit, onDelete }: MemoryListProps) {
  return (
    <div className="space-y-2 max-h-[400px] overflow-y-auto">
      {memories.length === 0 ? (
        <p className="text-gray-400 text-sm text-center py-8">
          No memories yet. Start chatting and I'll remember important things!
        </p>
      ) : (
        memories.map((memory) => (
          <MemoryCard
            key={memory.id}
            memory={memory}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))
      )}
    </div>
  );
}
```

### FR-3: Memory Card Component

Individual memory card with view/edit/delete actions.

```tsx
// components/memory/MemoryCard.tsx
export function MemoryCard({ memory, onEdit, onDelete }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedCaption, setEditedCaption] = useState(memory.caption);
  const [editedText, setEditedText] = useState(memory.full_text);

  const handleSave = () => {
    onEdit(memory.id, { caption: editedCaption, full_text: editedText });
    setIsEditing(false);
  };

  return (
    <div className="glass-card p-3 rounded-lg">
      {isEditing ? (
        <div className="space-y-2">
          <input
            value={editedCaption}
            onChange={(e) => setEditedCaption(e.target.value)}
            className="w-full bg-white/5 rounded px-2 py-1 text-sm"
            placeholder="Caption"
          />
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            className="w-full bg-white/5 rounded px-2 py-1 text-sm h-20"
            placeholder="Full content"
          />
          <div className="flex gap-2">
            <Button size="sm" onClick={handleSave}>Save</Button>
            <Button size="sm" variant="ghost" onClick={() => setIsEditing(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between">
            <div className="flex-1 cursor-pointer" onClick={() => setIsExpanded(!isExpanded)}>
              <p className="text-sm font-medium">{memory.caption}</p>
              <p className="text-xs text-gray-400">
                {formatDistanceToNow(new Date(memory.created_at))} ago
              </p>
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setIsEditing(true)}
                className="p-1 hover:bg-white/10 rounded"
                title="Edit"
              >
                <Pencil className="w-3 h-3" />
              </button>
              <button
                onClick={() => onDelete(memory.id)}
                className="p-1 hover:bg-red-500/20 text-red-400 rounded"
                title="Delete"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          </div>
          {isExpanded && (
            <div className="mt-2 pt-2 border-t border-white/10">
              <p className="text-sm text-gray-300">{memory.full_text}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

### FR-4: Memory Settings Sheet/Modal

Slide-out panel or modal for memory management.

```tsx
// components/memory/MemorySheet.tsx
export function MemorySheet({ open, onOpenChange }: MemorySheetProps) {
  const { memories, isLoading, refresh, editMemory, deleteMemory, clearAll } = useMemories();
  const [memoryEnabled, setMemoryEnabled] = useState(isMemoryEnabled());

  const handleToggle = (enabled: boolean) => {
    setMemoryEnabled(enabled);
    setMemoryEnabledStorage(enabled);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="glass-card w-[400px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-moss-500" />
            Memory
          </SheetTitle>
          <SheetDescription>
            Manage what I remember about you
          </SheetDescription>
        </SheetHeader>

        <div className="py-4 space-y-4">
          {/* Memory Toggle */}
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Enable Memory</p>
              <p className="text-xs text-gray-400">
                Remember things from our conversations
              </p>
            </div>
            <Switch
              checked={memoryEnabled}
              onCheckedChange={handleToggle}
            />
          </div>

          <Separator />

          {/* Memory Count */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-gray-400">
              {memories.length} memories stored
            </p>
            {memories.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearAll}
                className="text-red-400 hover:text-red-300"
              >
                Clear All
              </Button>
            )}
          </div>

          {/* Memory List */}
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : (
            <MemoryList
              memories={memories}
              onEdit={editMemory}
              onDelete={deleteMemory}
            />
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

### FR-5: Memory API Hooks

React hooks for memory management.

```tsx
// hooks/useMemories.ts
export function useMemories() {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const userId = getUserId();

  const refresh = useCallback(async () => {
    if (!userId) return;
    setIsLoading(true);
    try {
      const response = await fetch(`/api/memories?user_id=${userId}`);
      const data = await response.json();
      setMemories(data.memories || []);
    } catch (error) {
      console.error('Failed to fetch memories:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  const editMemory = useCallback(async (id: string, updates: Partial<Memory>) => {
    await fetch(`/api/memories/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, ...updates }),
    });
    refresh();
  }, [userId, refresh]);

  const deleteMemory = useCallback(async (id: string) => {
    await fetch(`/api/memories/${id}?user_id=${userId}`, {
      method: 'DELETE',
    });
    setMemories((prev) => prev.filter((m) => m.id !== id));
  }, [userId]);

  const clearAll = useCallback(async () => {
    if (!confirm('Delete all memories? This cannot be undone.')) return;
    await fetch(`/api/memories/clear?user_id=${userId}`, { method: 'DELETE' });
    setMemories([]);
  }, [userId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { memories, isLoading, refresh, editMemory, deleteMemory, clearAll };
}
```

### FR-6: Gateway Memory Proxy Endpoints

Add proxy endpoints to gateway for memory management.

```python
# gateway/janus_gateway/routers/memories.py
from fastapi import APIRouter, Query
import httpx

router = APIRouter(prefix="/api/memories", tags=["memories"])

@router.get("")
async def list_memories(user_id: str = Query(...)):
    """List all memories for a user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.memory_service_url}/memories/list",
            params={"user_id": user_id},
        )
        return response.json()

@router.patch("/{memory_id}")
async def update_memory(memory_id: str, body: dict):
    """Update a memory."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{settings.memory_service_url}/memories/{memory_id}",
            json=body,
        )
        return response.json()

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, user_id: str = Query(...)):
    """Delete a memory."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.memory_service_url}/memories/{memory_id}",
            params={"user_id": user_id},
        )
        return response.json()

@router.delete("/clear")
async def clear_memories(user_id: str = Query(...)):
    """Clear all memories for a user."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.memory_service_url}/memories/clear",
            params={"user_id": user_id},
        )
        return response.json()
```

### FR-7: Memory Service Endpoints (Update Spec 72)

Add required endpoints to memory service:

```python
# PATCH /memories/{memory_id}
@app.patch("/memories/{memory_id}")
async def update_memory(memory_id: str, body: MemoryUpdate):
    """Update a memory's caption and/or full_text."""
    # Validate user_id matches memory owner
    # Update fields
    pass

# DELETE /memories/clear
@app.delete("/memories/clear")
async def clear_memories(user_id: str = Query(...)):
    """Delete all memories for a user."""
    await db.execute(
        delete(Memory).where(Memory.user_id == user_id)
    )
    return {"deleted": True}
```

---

## UI/UX Design

### Memory Toggle Button (Header)

**Location:** Chat header, next to model selector

**States:**
- **Enabled:** Moss green brain icon with subtle pulse animation
- **Disabled:** Gray brain icon with slash

**Click Behavior:** Opens memory sheet panel

### Memory Sheet Panel

**Design:**
- Slide-out from right (400px width)
- Glass morphism background
- Dark theme consistent with app

**Layout:**
```
┌─────────────────────────────────┐
│  🧠 Memory                    X │
│  Manage what I remember about   │
│  you                            │
├─────────────────────────────────┤
│  Enable Memory          [====]  │
│  Remember things from our       │
│  conversations                  │
├─────────────────────────────────┤
│  12 memories stored  [Clear All]│
├─────────────────────────────────┤
│  ┌─────────────────────────┐    │
│  │ User has a dog named... │    │
│  │ 2 days ago        ✏️ 🗑️ │    │
│  └─────────────────────────┘    │
│  ┌─────────────────────────┐    │
│  │ Prefers dark mode...    │    │
│  │ 5 days ago        ✏️ 🗑️ │    │
│  └─────────────────────────┘    │
│  ...                            │
└─────────────────────────────────┘
```

### Memory Card Expanded

```
┌─────────────────────────────────┐
│ User has a dog named Max        │
│ 2 days ago                ✏️ 🗑️ │
├─────────────────────────────────┤
│ User mentioned having a golden  │
│ retriever named Max. They got   │
│ Max as a puppy 3 years ago and  │
│ he loves playing fetch.         │
└─────────────────────────────────┘
```

### Memory Card Edit Mode

```
┌─────────────────────────────────┐
│ [User has a dog named Max     ] │
│ ┌─────────────────────────────┐ │
│ │ User mentioned having a     │ │
│ │ golden retriever named Max. │ │
│ │ They got Max as a puppy 3   │ │
│ │ years ago...                │ │
│ └─────────────────────────────┘ │
│ [Save] [Cancel]                 │
└─────────────────────────────────┘
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `ui/src/components/memory/MemorySheet.tsx` | Main memory panel |
| `ui/src/components/memory/MemoryList.tsx` | Memory list component |
| `ui/src/components/memory/MemoryCard.tsx` | Individual memory card |
| `ui/src/hooks/useMemories.ts` | Memory management hooks |
| `gateway/janus_gateway/routers/memories.py` | Gateway proxy endpoints |

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/components/ChatArea.tsx` | Add memory toggle → open sheet |
| `ui/src/components/MemoryToggle.tsx` | Click opens sheet instead of just toggle |
| `gateway/janus_gateway/main.py` | Include memories router |
| `memory-service/.../main.py` | Add PATCH and clear endpoints |

---

## Acceptance Criteria

- [ ] Memory toggle button opens management panel
- [ ] User can view all their memories
- [ ] User can expand memories to see full content
- [ ] User can edit memory caption and content
- [ ] User can delete individual memories
- [ ] User can clear all memories (with confirmation)
- [ ] Memory enable/disable toggle works
- [ ] Panel is responsive and scrollable
- [ ] Design is subtle and unobtrusive

---

## Testing Checklist

- [ ] Memory list loads correctly
- [ ] Empty state shows helpful message
- [ ] Memory cards expand/collapse
- [ ] Edit mode saves changes
- [ ] Delete removes memory from list
- [ ] Clear all requires confirmation
- [ ] Toggle persists to localStorage
- [ ] Panel closes on outside click
- [ ] Responsive on mobile

---

## Notes

- Memory management should feel like a secondary feature, not in-your-face
- The brain icon in header serves dual purpose: status indicator + access point
- Consider adding search/filter in future if users accumulate many memories
- Export functionality can be added later

NR_OF_TRIES: 1
