import asyncio

import pytest

from app.services import gemini_service


class _DummyModel:
    async def generate_content_async(self, *, contents, generation_config):
        return {"contents": contents, "generation_config": generation_config}


class _DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text


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


@pytest.mark.asyncio
async def test_analyze_food_image_parses_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    service = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
    service.language = "ko"

    async def fake_generate_with_model_fallback(*, contents, generation_config):
        return _DummyResponse(
            '[{"name":"우유","quantity":1,"unit":"L","category":"냉장","confidence":0.95}]'
        )

    monkeypatch.setattr(service, "_generate_with_model_fallback", fake_generate_with_model_fallback)

    items = await service.analyze_food_image(b"image-bytes", "image/jpeg")

    assert len(items) == 1
    assert items[0].name == "우유"
    assert items[0].category == "냉장"


@pytest.mark.asyncio
async def test_analyze_food_image_returns_empty_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    service = gemini_service.GeminiService.__new__(gemini_service.GeminiService)
    service.language = "ko"

    async def fake_generate_with_model_fallback(*, contents, generation_config):
        return _DummyResponse("not-json")

    monkeypatch.setattr(service, "_generate_with_model_fallback", fake_generate_with_model_fallback)

    items = await service.analyze_food_image(b"image-bytes", "image/jpeg")
    assert items == []
