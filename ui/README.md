# Janus Chat UI

ChatGPT-like interface for the Janus gateway with streaming support and reasoning visualization.

## Features

- Session list with new chat and history
- Real-time streaming with incremental rendering
- Markdown rendering with syntax highlighting
- Image upload (base64 data URLs)
- Reasoning panel support for reasoning_content
- Competitor selector (baseline only in MVP)
- Artifact links with download support
- Voice input with speech-to-text transcription

## Installation

```bash
npm install
```

## Running

```bash
# Development mode
npm run dev

# Production build
npm run build
npm start
```

## Testing

```bash
# Run tests
npm test

# Type checking
npm run typecheck

# Linting
npm run lint
```

## Project Structure

```
ui/
├── src/
│   ├── app/           # Next.js app router
│   │   ├── layout.tsx # Root layout
│   │   └── page.tsx   # Main chat page
│   ├── components/    # React components
│   │   ├── ChatArea.tsx
│   │   ├── ChatInput.tsx
│   │   ├── MessageBubble.tsx
│   │   └── Sidebar.tsx
│   ├── lib/           # Utilities
│   │   └── api.ts     # Gateway API client
│   ├── store/         # State management
│   │   └── chat.ts    # Chat state (zustand)
│   └── types/         # TypeScript types
│       └── chat.ts
└── ...
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_GATEWAY_URL` | `http://localhost:8000` | Janus gateway URL |
| `NEXT_PUBLIC_ENABLE_VOICE_INPUT` | `false` | Toggle voice input UI |
| `CHUTES_OAUTH_CLIENT_ID` | - | Chutes OAuth client ID |
| `CHUTES_OAUTH_CLIENT_SECRET` | - | Chutes OAuth client secret |
| `CHUTES_OAUTH_REDIRECT_URI` | `http://localhost:3000/api/auth/callback` | OAuth callback URL |
| `CHUTES_OAUTH_COOKIE_SECRET` | - | Optional secret for OAuth cookie encryption |

## API Integration

The UI communicates with the Janus Gateway via:

- `POST /v1/chat/completions` - Send chat messages (SSE streaming)
- `GET /v1/models` - List available competitors
- `GET /v1/artifacts/{id}` - Retrieve artifacts

## Health Check

The UI is ready when it's accessible at `http://localhost:3000` and can reach the gateway.
