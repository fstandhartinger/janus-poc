# Spec 97: CLI Agent Warm Pool

## Status: COMPLETE

## Context / Why

Currently, when a complex request hits the baseline-agent-cli, it must:
1. Create a new Sandy sandbox
2. Provision the CLI agent (install dependencies, configure)
3. Then start processing the request

This cold-start adds 10-30 seconds to the first response. For a production-quality experience, we need pre-warmed sandboxes ready to handle requests immediately.

## Goals

- Reduce first-response latency for complex requests
- Maintain a pool of ready-to-use Sandy sandboxes
- Implement sandbox recycling for repeat requests
- Define pool sizing and lifecycle management

## Functional Requirements

### FR-1: Warm Pool Manager

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/warm_pool.py

class WarmPoolManager:
    """Manages a pool of pre-warmed Sandy sandboxes."""

    def __init__(
        self,
        sandy_service: SandyService,
        pool_size: int = 2,
        max_age_seconds: int = 3600,
    ):
        self.sandy = sandy_service
        self.pool_size = pool_size
        self.max_age = max_age_seconds
        self._pool: list[WarmSandbox] = []
        self._lock = asyncio.Lock()

    async def start(self):
        """Initialize pool with warm sandboxes."""
        await self._fill_pool()
        # Start background maintenance task
        asyncio.create_task(self._maintenance_loop())

    async def acquire(self) -> WarmSandbox:
        """Get a warm sandbox from the pool."""
        async with self._lock:
            if self._pool:
                sandbox = self._pool.pop(0)
                # Trigger background refill
                asyncio.create_task(self._fill_pool())
                return sandbox
            # Pool empty - create on demand
            return await self._create_warm_sandbox()

    async def release(self, sandbox: WarmSandbox, reusable: bool = True):
        """Return sandbox to pool or terminate."""
        if reusable and len(self._pool) < self.pool_size:
            sandbox.reset()
            async with self._lock:
                self._pool.append(sandbox)
        else:
            await sandbox.terminate()

    async def _fill_pool(self):
        """Fill pool to target size."""
        while len(self._pool) < self.pool_size:
            sandbox = await self._create_warm_sandbox()
            async with self._lock:
                self._pool.append(sandbox)

    async def _maintenance_loop(self):
        """Periodic health check and refresh."""
        while True:
            await asyncio.sleep(60)
            await self._health_check()
            await self._expire_old_sandboxes()
```

### FR-2: Warm Sandbox Lifecycle

```python
@dataclass
class WarmSandbox:
    """A pre-warmed sandbox ready for use."""
    sandbox_id: str
    created_at: datetime
    last_used: datetime | None = None
    request_count: int = 0

    async def execute(self, request: AgentRequest) -> AsyncIterator[str]:
        """Execute agent request in this sandbox."""
        self.last_used = datetime.utcnow()
        self.request_count += 1
        # ... execute via Sandy API

    def reset(self):
        """Reset sandbox state for reuse."""
        # Clear any session-specific state
        pass

    async def terminate(self):
        """Clean up sandbox resources."""
        await sandy_client.terminate(self.sandbox_id)
```

### FR-3: Integration with Main Request Handler

```python
# In main.py

@app.on_event("startup")
async def startup():
    global warm_pool
    warm_pool = WarmPoolManager(sandy_service, pool_size=settings.warm_pool_size)
    await warm_pool.start()

async def handle_complex_request(request: ChatCompletionRequest):
    sandbox = await warm_pool.acquire()
    try:
        async for chunk in sandbox.execute(request):
            yield chunk
        # Request succeeded - sandbox can be reused
        await warm_pool.release(sandbox, reusable=True)
    except Exception as e:
        # Error - don't reuse this sandbox
        await warm_pool.release(sandbox, reusable=False)
        raise
```

### FR-4: Configuration

```python
# In settings.py

class Settings(BaseSettings):
    # Warm pool settings
    warm_pool_enabled: bool = True
    warm_pool_size: int = 2  # Number of warm sandboxes to maintain
    warm_pool_max_age: int = 3600  # Max sandbox age in seconds
    warm_pool_max_requests: int = 10  # Max requests per sandbox before refresh
```

### FR-5: Health Monitoring

```python
# Add to health endpoint

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "warm_pool": {
            "enabled": settings.warm_pool_enabled,
            "size": len(warm_pool._pool) if warm_pool else 0,
            "target": settings.warm_pool_size,
        }
    }
```

## Acceptance Criteria

- [ ] Warm pool initializes on service startup
- [ ] Complex requests use warm sandboxes (reduced latency)
- [ ] Pool refills automatically after sandbox acquisition
- [ ] Old/unhealthy sandboxes are expired
- [ ] Sandboxes are recycled when safe, terminated on error
- [ ] Health endpoint shows pool status
- [ ] Configuration via environment variables

## Files to Create/Modify

```
baseline-agent-cli/janus_baseline_agent_cli/
├── services/
│   └── warm_pool.py    # NEW: Warm pool manager
├── main.py             # MODIFY: Integrate warm pool
└── config.py           # MODIFY: Add pool settings
```

## Testing

```python
async def test_warm_pool_acquisition():
    pool = WarmPoolManager(mock_sandy, pool_size=2)
    await pool.start()

    # Pool should be filled
    assert len(pool._pool) == 2

    # Acquire should be fast (no cold start)
    start = time.time()
    sandbox = await pool.acquire()
    assert time.time() - start < 0.1  # Near instant

    # Pool should refill
    await asyncio.sleep(0.5)
    assert len(pool._pool) == 2  # Refilled

async def test_sandbox_recycling():
    pool = WarmPoolManager(mock_sandy, pool_size=1)
    await pool.start()

    sandbox = await pool.acquire()
    await pool.release(sandbox, reusable=True)

    # Same sandbox should be reused
    sandbox2 = await pool.acquire()
    assert sandbox2.sandbox_id == sandbox.sandbox_id
```

## Performance Target

- Cold start (current): 15-30 seconds
- Warm start (with pool): <2 seconds

## Related Specs

- Spec 08: Sandy Integration
- Spec 43: Agent Sandbox Management

NR_OF_TRIES: 2
