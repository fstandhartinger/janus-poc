from uuid import uuid4

import pytest

from memory_service.services import llm


@pytest.mark.asyncio
async def test_extract_store_and_list(client, monkeypatch):
    user_id = uuid4()

    async def fake_extract(_conversation):
        return [llm.ExtractedMemory(caption="User has a dog", full_text="Dog named Max")]

    monkeypatch.setattr(llm, "extract_memories", fake_extract)

    response = await client.post(
        "/memories/extract",
        json={
            "user_id": str(user_id),
            "conversation": [
                {"role": "user", "content": "My dog's name is Max"},
                {"role": "assistant", "content": "Nice!"},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["memories_saved"]
    assert payload["total_user_memories"] == 1

    list_response = await client.get("/memories/list", params={"user_id": str(user_id)})
    assert list_response.status_code == 200
    memories = list_response.json()["memories"]
    assert len(memories) == 1
    assert memories[0]["caption"] == "User has a dog"


@pytest.mark.asyncio
async def test_relevant_memories_returns_matches(client, monkeypatch):
    user_id = uuid4()

    async def fake_extract(_conversation):
        return [
            llm.ExtractedMemory(caption="User has a cat", full_text="Cat named Nori"),
            llm.ExtractedMemory(caption="User likes tea", full_text="Prefers oolong"),
        ]

    monkeypatch.setattr(llm, "extract_memories", fake_extract)

    extract_response = await client.post(
        "/memories/extract",
        json={
            "user_id": str(user_id),
            "conversation": [
                {"role": "user", "content": "My cat is named Nori"},
                {"role": "assistant", "content": "Adorable!"},
            ],
        },
    )
    assert extract_response.status_code == 200
    saved = extract_response.json()["memories_saved"]
    relevant_id = saved[0]["id"]

    async def fake_relevant(_prompt, _memories):
        return [relevant_id]

    monkeypatch.setattr(llm, "select_relevant_ids", fake_relevant)

    relevant_response = await client.get(
        "/memories/relevant",
        params={"user_id": str(user_id), "prompt": "What should I buy for my cat?"},
    )
    assert relevant_response.status_code == 200
    memories = relevant_response.json()["memories"]
    assert len(memories) == 1
    assert memories[0]["id"] == relevant_id


@pytest.mark.asyncio
async def test_empty_conversation_skips_llm(client, monkeypatch):
    user_id = uuid4()
    called = {"value": False}

    async def fake_extract(_conversation):
        called["value"] = True
        return []

    monkeypatch.setattr(llm, "extract_memories", fake_extract)

    response = await client.post(
        "/memories/extract",
        json={"user_id": str(user_id), "conversation": []},
    )
    assert response.status_code == 200
    assert response.json()["memories_saved"] == []
    assert called["value"] is False


@pytest.mark.asyncio
async def test_rate_limit_enforced(client, monkeypatch):
    import memory_service.main as main

    previous_limit = main.settings.rate_limit_per_minute
    main.settings.rate_limit_per_minute = 2
    main._rate_limit.clear()

    user_id = uuid4()
    for _ in range(2):
        response = await client.get("/memories/list", params={"user_id": str(user_id)})
        assert response.status_code == 200

    third = await client.get("/memories/list", params={"user_id": str(user_id)})
    assert third.status_code == 429

    main.settings.rate_limit_per_minute = previous_limit
    main._rate_limit.clear()


@pytest.mark.asyncio
async def test_max_memories_limit(client, monkeypatch):
    import memory_service.main as main

    main.settings.max_memories_per_user = 2
    main.settings.rate_limit_per_minute = 1000
    main._rate_limit.clear()

    counter = {"value": 0}

    async def fake_extract(_conversation):
        counter["value"] += 1
        return [
            llm.ExtractedMemory(
                caption=f"memory {counter['value']}",
                full_text=f"detail {counter['value']}",
            )
        ]

    monkeypatch.setattr(llm, "extract_memories", fake_extract)

    user_id = uuid4()
    saved_ids = []
    for idx in range(3):
        response = await client.post(
            "/memories/extract",
            json={
                "user_id": str(user_id),
                "conversation": [
                    {"role": "user", "content": f"memory {idx}"},
                    {"role": "assistant", "content": "noted"},
                ],
            },
        )
        saved_ids.append(response.json()["memories_saved"][0]["id"])

    list_response = await client.get("/memories/list", params={"user_id": str(user_id)})
    memories = list_response.json()["memories"]
    assert len(memories) == 2
    returned_ids = {mem["id"] for mem in memories}
    assert saved_ids[0] not in returned_ids


@pytest.mark.asyncio
async def test_invalid_user_id_returns_422(client):
    response = await client.get("/memories/list", params={"user_id": "not-a-uuid"})
    assert response.status_code == 422
