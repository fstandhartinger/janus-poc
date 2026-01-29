from janus_gateway.models import CompetitorInfo
from janus_gateway.services.arena import ArenaPromptStore, ArenaService
from janus_gateway.services.competitor_registry import CompetitorRegistry


def test_arena_pair_distinct():
    registry = CompetitorRegistry()
    registry.register(
        CompetitorInfo(
            id="secondary-model",
            name="Secondary Model",
            description="Test competitor",
            url="http://localhost:8082",
            enabled=True,
            is_baseline=False,
        )
    )
    service = ArenaService(registry)
    model_a, model_b = service.get_arena_pair()
    assert model_a != model_b


def test_prompt_store_marks_vote():
    store = ArenaPromptStore(ttl_seconds=60)
    record = store.create("Hello world", "model-a", "model-b", user_id=None)
    fetched = store.get(record.prompt_id)
    assert fetched is not None
    assert fetched.voted is False
    store.mark_voted(record.prompt_id)
    fetched = store.get(record.prompt_id)
    assert fetched is not None
    assert fetched.voted is True
