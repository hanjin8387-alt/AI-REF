import asyncio

import pytest

from app.services import gemini_service


class _DummyModel:
    async def generate_content_async(self, *, contents, generation_config):
        return {"contents": contents, "generation_config": generation_config}


@pytest.mark.asyncio
async def test_generate_with_model_fallback_uses_explicit_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_wait_for(awaitable, timeout):
        captured["timeout"] = timeout
        return await awaitable

    service = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
    service._active_model_index = 0
    service._model_candidates = ["model-a"]
    service.model = _DummyModel()

    monkeypatch.setattr(gemini_service.asyncio, "wait_for", fake_wait_for)

    result = await service._generate_with_model_fallback(
        contents=[{"key": "value"}],
        generation_config=object(),
    )

    assert captured["timeout"] == gemini_service.GEMINI_TIMEOUT_SECONDS
    assert result["contents"] == [{"key": "value"}]


@pytest.mark.asyncio
async def test_generate_with_model_fallback_raises_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_wait_for(awaitable, timeout):
        if hasattr(awaitable, "close"):
            awaitable.close()
        raise asyncio.TimeoutError

    service = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
    service._active_model_index = 0
    service._model_candidates = ["model-a"]
    service.model = _DummyModel()

    monkeypatch.setattr(gemini_service.asyncio, "wait_for", fake_wait_for)

    with pytest.raises(asyncio.TimeoutError):
        await service._generate_with_model_fallback(
            contents=[{"key": "value"}],
            generation_config=object(),
        )
