# Spec 99: Arena-Style User Preference Comparison (Optional)

## Status: NOT STARTED

## Context / Why

Automated benchmarks can be gamed. To get real signal on which implementations users prefer, we need an arena-style comparison (like LMSys Arena / Chatbot Arena) where users compare responses side-by-side without knowing which model produced which response.

**This feature is OPTIONAL** - users must explicitly opt-in to participate.

## Goals

- Implement side-by-side comparison mode in chat UI
- Blind A/B testing of different baselines/implementations
- Collect user preference votes
- Compute ELO-style ratings
- Prevent gaming/botting

## Functional Requirements

### FR-1: Opt-In Arena Mode

Users can enable arena mode from settings or via a toggle in chat.

```typescript
// In ChatSettings or header
function ArenaToggle() {
  const [arenaEnabled, setArenaEnabled] = useLocalStorage('arena_mode', false);

  return (
    <div className="flex items-center gap-2">
      <Switch
        checked={arenaEnabled}
        onChange={setArenaEnabled}
      />
      <span className="text-sm text-white/60">
        Arena Mode (compare responses)
      </span>
    </div>
  );
}
```

### FR-2: Side-by-Side UI

When arena mode is enabled, show two responses for each query.

```typescript
// ArenaComparison.tsx
function ArenaComparison({
  promptId,
  responseA,
  responseB,
  onVote
}: ArenaProps) {
  const [voted, setVoted] = useState(false);
  const [revealed, setRevealed] = useState(false);

  const handleVote = (winner: 'A' | 'B' | 'tie' | 'both_bad') => {
    onVote({ promptId, winner });
    setVoted(true);
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Response A */}
      <div className="glass-card p-4">
        <div className="text-sm text-white/40 mb-2">Response A</div>
        <MarkdownRenderer content={responseA.content} />
      </div>

      {/* Response B */}
      <div className="glass-card p-4">
        <div className="text-sm text-white/40 mb-2">Response B</div>
        <MarkdownRenderer content={responseB.content} />
      </div>

      {/* Voting buttons */}
      {!voted && (
        <div className="col-span-2 flex justify-center gap-4 mt-4">
          <Button onClick={() => handleVote('A')}>A is better</Button>
          <Button onClick={() => handleVote('B')}>B is better</Button>
          <Button variant="ghost" onClick={() => handleVote('tie')}>Tie</Button>
          <Button variant="ghost" onClick={() => handleVote('both_bad')}>Both bad</Button>
        </div>
      )}

      {/* Reveal models after voting */}
      {voted && (
        <div className="col-span-2 text-center">
          <Button variant="link" onClick={() => setRevealed(true)}>
            Reveal models
          </Button>
          {revealed && (
            <div className="text-sm text-white/60 mt-2">
              A: {responseA.model} | B: {responseB.model}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

### FR-3: Random Model Assignment

Gateway randomly assigns two different models for arena requests.

```python
# gateway/janus_gateway/services/arena.py

class ArenaService:
    def __init__(self, available_models: list[str]):
        self.models = available_models

    def get_arena_pair(self, exclude: str | None = None) -> tuple[str, str]:
        """Get two random different models for comparison."""
        available = [m for m in self.models if m != exclude]
        if len(available) < 2:
            raise ValueError("Need at least 2 models for arena")

        pair = random.sample(available, 2)
        random.shuffle(pair)  # Randomize A/B assignment
        return tuple(pair)

# In chat router
@router.post("/v1/chat/completions/arena")
async def arena_chat(request: ChatCompletionRequest):
    model_a, model_b = arena_service.get_arena_pair()

    # Run both in parallel
    response_a, response_b = await asyncio.gather(
        forward_to_competitor(request, model_a),
        forward_to_competitor(request, model_b),
    )

    return ArenaResponse(
        prompt_id=str(uuid4()),
        response_a=response_a,
        response_b=response_b,
        # Don't reveal models until after vote
    )
```

### FR-4: Vote Collection & Storage

```python
# gateway/janus_gateway/models/arena.py

class ArenaVote(BaseModel):
    prompt_id: str
    winner: Literal["A", "B", "tie", "both_bad"]
    model_a: str  # Stored server-side, not sent to client
    model_b: str
    user_id: str | None
    timestamp: datetime
    prompt_hash: str  # For deduplication

# Store votes
@router.post("/api/arena/vote")
async def submit_vote(vote: VoteRequest):
    # Retrieve prompt info (with model assignments)
    prompt_info = await get_arena_prompt(vote.prompt_id)

    await store_vote(ArenaVote(
        prompt_id=vote.prompt_id,
        winner=vote.winner,
        model_a=prompt_info.model_a,
        model_b=prompt_info.model_b,
        user_id=current_user_id(),
        timestamp=datetime.utcnow(),
        prompt_hash=hash_prompt(prompt_info.prompt),
    ))

    return {"status": "recorded"}
```

### FR-5: ELO Rating Calculation

```python
# scoring-service/scoring_service/arena_elo.py

def update_elo(
    rating_a: float,
    rating_b: float,
    winner: str,
    k: float = 32.0,
) -> tuple[float, float]:
    """Update ELO ratings based on match result."""
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1 - expected_a

    if winner == "A":
        score_a, score_b = 1.0, 0.0
    elif winner == "B":
        score_a, score_b = 0.0, 1.0
    else:  # tie
        score_a, score_b = 0.5, 0.5

    new_rating_a = rating_a + k * (score_a - expected_a)
    new_rating_b = rating_b + k * (score_b - expected_b)

    return new_rating_a, new_rating_b

def compute_leaderboard() -> list[dict]:
    """Compute arena leaderboard from all votes."""
    ratings = defaultdict(lambda: 1500.0)  # Starting ELO

    for vote in get_all_votes():
        if vote.winner in ("A", "B", "tie"):
            ratings[vote.model_a], ratings[vote.model_b] = update_elo(
                ratings[vote.model_a],
                ratings[vote.model_b],
                vote.winner,
            )

    return sorted(
        [{"model": k, "elo": v} for k, v in ratings.items()],
        key=lambda x: x["elo"],
        reverse=True,
    )
```

### FR-6: Anti-Botting Measures

```python
# Basic anti-gaming measures

def validate_vote(vote: VoteRequest, user_info: UserInfo) -> bool:
    # 1. Rate limit per user
    recent_votes = count_votes_since(user_info.id, minutes=60)
    if recent_votes > 50:
        raise TooManyVotesError()

    # 2. Minimum response view time
    prompt_info = get_arena_prompt(vote.prompt_id)
    view_duration = datetime.utcnow() - prompt_info.created_at
    if view_duration < timedelta(seconds=5):
        raise VoteTooFastError()

    # 3. Require some account age or activity
    if user_info.created_at > datetime.utcnow() - timedelta(days=1):
        raise AccountTooNewError()

    return True
```

## UI Flow

1. User enables "Arena Mode" in settings (opt-in)
2. User sends a message
3. UI shows two responses side-by-side (A and B)
4. User votes for preferred response (or tie/both bad)
5. After voting, user can reveal which models produced each response
6. Vote is recorded for ELO calculation
7. Arena leaderboard shows on Competition page

## Acceptance Criteria

- [ ] Arena mode is opt-in only
- [ ] Side-by-side UI works on desktop (responsive on mobile)
- [ ] Models are randomly assigned and blinded
- [ ] Votes are stored with proper attribution
- [ ] ELO ratings calculated and displayed
- [ ] Basic anti-botting measures in place
- [ ] Arena leaderboard on competition page

## Files to Create/Modify

```
ui/src/
├── components/
│   └── arena/
│       ├── ArenaToggle.tsx
│       ├── ArenaComparison.tsx
│       └── ArenaLeaderboard.tsx
├── hooks/
│   └── useArena.ts

gateway/janus_gateway/
├── routers/
│   └── arena.py           # NEW
├── services/
│   └── arena.py           # NEW
└── models/
    └── arena.py           # NEW

scoring-service/scoring_service/
└── arena_elo.py           # NEW
```

## Related Specs

- Spec 19: Competition Page
- Spec 56: Scoring Service Backend
- Spec 98: Real Benchmark Dataset

NR_OF_TRIES: 0
