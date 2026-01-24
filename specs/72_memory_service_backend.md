# Spec 72: Memory Service Backend

**Status:** NOT STARTED
**Priority:** High
**Complexity:** Medium
**Prerequisites:** None (standalone service)

---

## Overview

Create a simple memory service API that stores and retrieves user memories from conversations. The service is deployed to Render (via MCP) with a PostgreSQL database. After each chat response completes, the Janus baseline implementations call this service to potentially memorize important information from the conversation.

---

## Functional Requirements

### FR-1: Memory Service API

Deploy a FastAPI service to Render with the following endpoints:

#### POST /memories/extract
Extract and save memories from a conversation.

**Request:**
```json
{
  "user_id": "uuid-string",
  "conversation": [
    {"role": "user", "content": "My dog's name is Max and he's a golden retriever"},
    {"role": "assistant", "content": "That's a lovely name for a golden retriever!"}
  ]
}
```

**Response:**
```json
{
  "memories_saved": [
    {
      "id": "mem_abc123",
      "caption": "User has a dog named Max (golden retriever)",
      "created_at": "2024-01-24T12:00:00Z"
    }
  ],
  "total_user_memories": 15
}
```

**Logic:**
1. Pass conversation to fast LLM (GLM 4.7 Fast via Chutes API)
2. LLM decides what's worth memorizing using this prompt:
```
You are a memory extraction assistant. Analyze this conversation and identify facts worth remembering about the user for future sessions.

Extract ONLY:
- Personal preferences (favorite things, dislikes)
- Important personal information (names, relationships, pets, locations)
- Technical preferences (coding style, tools they use)
- Ongoing projects or goals
- Specific facts they want to remember

DO NOT extract:
- Temporary context (what they're working on RIGHT NOW)
- General knowledge or facts
- Conversational pleasantries
- Things already commonly known

Return JSON array of memories to save:
[
  {
    "caption": "Brief 1-line summary (max 100 chars)",
    "full_text": "Full context with details (max 500 chars)"
  }
]

If nothing worth memorizing, return empty array: []

Conversation:
<conversation>
{CONVERSATION_HERE}
</conversation>
```

3. Save extracted memories to Postgres

#### GET /memories/relevant
Get memories relevant to a user's current prompt.

**Request:**
```
GET /memories/relevant?user_id=uuid&prompt=What%20should%20I%20name%20my%20new%20cat
```

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "caption": "User has a dog named Max (golden retriever)"
    },
    {
      "id": "mem_def456",
      "caption": "User prefers short, classic pet names"
    }
  ]
}
```

**Logic:**
1. Load ALL memory captions for user_id from Postgres
2. Pass captions + user prompt to fast LLM with this prompt:
```
You are a memory relevance assistant. Given a user's prompt and their stored memories, select which memories might be relevant to help answer their question.

User's prompt:
<prompt>
{USER_PROMPT}
</prompt>

Available memories (id: caption):
<memories>
{MEMORY_LIST}
</memories>

Return JSON array of relevant memory IDs, most relevant first. If none are relevant, return empty array: []

Example: ["mem_abc123", "mem_def456"]
```

3. Return matched memory IDs and captions

#### GET /memories/full
Get full memory content for investigation (used by agent tool).

**Request:**
```
GET /memories/full?user_id=uuid&ids=mem_abc123,mem_def456
```

**Response:**
```json
{
  "memories": [
    {
      "id": "mem_abc123",
      "caption": "User has a dog named Max (golden retriever)",
      "full_text": "User mentioned having a golden retriever named Max. They got Max as a puppy 3 years ago.",
      "created_at": "2024-01-24T12:00:00Z"
    }
  ]
}
```

#### DELETE /memories/{memory_id}
Delete a specific memory.

**Request:**
```
DELETE /memories/mem_abc123?user_id=uuid
```

#### GET /memories/list
List all memories for a user (for debugging/admin).

**Request:**
```
GET /memories/list?user_id=uuid&limit=50&offset=0
```

---

### FR-2: PostgreSQL Database Schema

```sql
CREATE TABLE memories (
    id VARCHAR(20) PRIMARY KEY,  -- mem_<nanoid>
    user_id UUID NOT NULL,
    caption VARCHAR(100) NOT NULL,
    full_text VARCHAR(500) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_memories_user_id (user_id),
    INDEX idx_memories_created_at (created_at)
);

-- Optional: track extraction logs for debugging
CREATE TABLE memory_extractions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL,
    conversation_hash VARCHAR(64),  -- SHA256 of conversation
    memories_extracted INTEGER DEFAULT 0,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

### FR-3: LLM Configuration

- **Model:** GLM-4-9B-0414-fast (via Chutes API `https://llm.chutes.ai/v1`)
- **API Key:** Use `CHUTES_API_KEY` environment variable
- **Temperature:** 0.1 (deterministic for consistent extraction)
- **Max Tokens:** 1000

---

### FR-4: Rate Limiting & Limits

- Max 100 memories per user (delete oldest when exceeded)
- Max 1 extraction call per conversation (track via conversation_hash)
- Rate limit: 60 requests/minute per user_id

---

## Technical Requirements

### TR-1: Project Structure

```
memory-service/
├── memory_service/
│   ├── __init__.py
│   ├── main.py           # FastAPI app
│   ├── config.py         # Settings (Pydantic)
│   ├── database.py       # SQLAlchemy/asyncpg setup
│   ├── models.py         # Pydantic request/response models
│   ├── schemas.py        # SQLAlchemy ORM models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── memory.py     # Memory CRUD operations
│   │   └── llm.py        # LLM extraction/relevance
│   └── utils.py          # ID generation, hashing
├── pyproject.toml
├── Dockerfile
├── render.yaml           # Render deployment config
└── README.md
```

### TR-2: Dependencies

```toml
[project]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "asyncpg>=0.29.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "httpx>=0.27.0",
    "nanoid>=2.0.0",
]
```

### TR-3: Environment Variables

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/memory_db
CHUTES_API_KEY=your-chutes-api-key
DEBUG=false
LOG_LEVEL=INFO
```

### TR-4: Render Deployment

Use Render MCP to deploy:
1. Create Postgres database (`janus-memory-db`)
2. Create web service (`janus-memory-service`)
3. Link database to service
4. Set environment variables

```yaml
# render.yaml
services:
  - type: web
    name: janus-memory-service
    runtime: python
    buildCommand: pip install -e .
    startCommand: uvicorn memory_service.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: janus-memory-db
          property: connectionString
      - key: CHUTES_API_KEY
        sync: false

databases:
  - name: janus-memory-db
    plan: free
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `memory-service/memory_service/__init__.py` | Package init |
| `memory-service/memory_service/main.py` | FastAPI app with all endpoints |
| `memory-service/memory_service/config.py` | Pydantic settings |
| `memory-service/memory_service/database.py` | Database connection and session |
| `memory-service/memory_service/models.py` | Request/response Pydantic models |
| `memory-service/memory_service/schemas.py` | SQLAlchemy ORM models |
| `memory-service/memory_service/services/memory.py` | Memory CRUD |
| `memory-service/memory_service/services/llm.py` | LLM extraction/relevance |
| `memory-service/memory_service/utils.py` | Utilities |
| `memory-service/pyproject.toml` | Project configuration |
| `memory-service/Dockerfile` | Container build |
| `memory-service/render.yaml` | Render deployment |
| `memory-service/README.md` | Documentation |

---

## Deployment Steps

1. Create `memory-service/` directory structure
2. Implement all service code
3. Test locally with Docker Compose (Postgres + service)
4. Use Render MCP to:
   - Create Postgres database
   - Create web service
   - Deploy and verify

---

## Acceptance Criteria

- [ ] All API endpoints implemented and functional
- [ ] PostgreSQL database deployed on Render
- [ ] Memory extraction works correctly with LLM
- [ ] Relevance matching returns appropriate memories
- [ ] Rate limiting prevents abuse
- [ ] Health check endpoint returns 200
- [ ] Service accessible at `https://janus-memory-service.onrender.com`

---

## Testing Checklist

- [ ] Unit tests for memory extraction logic
- [ ] Unit tests for relevance matching
- [ ] Integration test: extract → store → retrieve flow
- [ ] Test rate limiting behavior
- [ ] Test max memories limit (oldest deletion)
- [ ] Test with empty conversations (no extraction)
- [ ] Test with invalid user_id

---

## Notes

- This service runs on the SAME sandbox as the baseline implementations for now
- In production, this would be a shared service across all Janus instances
- The service is intentionally simple - complexity can be added later
- Memory extraction happens AFTER response is sent (non-blocking)
