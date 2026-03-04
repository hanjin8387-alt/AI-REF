from __future__ import annotations

import pytest

from app.services.gemini_service import GeminiContractError, GeminiService


class _Response:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.mark.asyncio
async def test_analyze_food_image_raises_on_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiService.__new__(GeminiService)
    service.language = "ko"
    service._model_candidates = ["model-a"]
    service._active_model_index = 0
    service.model = object()

    async def _fake_generate_with_model_fallback(*, contents, generation_config):
        return _Response("not-json")

    monkeypatch.setattr(service, "_generate_with_model_fallback", _fake_generate_with_model_fallback)

    with pytest.raises(GeminiContractError) as exc:
        await service.analyze_food_image(b"img", "image/jpeg")
    assert exc.value.code == "invalid_json"


@pytest.mark.asyncio
async def test_generate_recipe_recommendations_raises_on_invalid_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiService.__new__(GeminiService)
    service.language = "ko"
    service._model_candidates = ["model-a"]
    service._active_model_index = 0
    service.model = object()

    async def _fake_generate_with_model_fallback(*, contents, generation_config):
        return _Response('{"not":"array"}')

    monkeypatch.setattr(service, "_generate_with_model_fallback", _fake_generate_with_model_fallback)

    with pytest.raises(GeminiContractError) as exc:
        await service.generate_recipe_recommendations([{"name": "우유", "expiry_days": 1}], max_recipes=3)
    assert exc.value.code == "invalid_shape"


@pytest.mark.asyncio
async def test_analyze_food_image_sets_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiService.__new__(GeminiService)
    service.language = "ko"
    service._model_candidates = ["model-a"]
    service._active_model_index = 0
    service.model = object()
    captured: dict[str, object] = {}

    async def _fake_generate_with_model_fallback(*, contents, generation_config):
        captured["generation_config"] = generation_config
        return _Response("[]")

    monkeypatch.setattr(service, "_generate_with_model_fallback", _fake_generate_with_model_fallback)
    await service.analyze_food_image(b"img", "image/jpeg")

    generation_config = captured.get("generation_config")
    assert generation_config is not None
    response_schema = generation_config.response_schema
    assert isinstance(response_schema, dict)
    assert response_schema.get("type") == "array"


@pytest.mark.asyncio
async def test_analyze_receipt_image_sets_response_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    service = GeminiService.__new__(GeminiService)
    service.language = "ko"
    service._model_candidates = ["model-a"]
    service._active_model_index = 0
    service.model = object()
    captured: dict[str, object] = {}

    async def _fake_generate_with_model_fallback(*, contents, generation_config):
        captured["generation_config"] = generation_config
        return _Response('{"raw_text":"ok","items":[]}')

    monkeypatch.setattr(service, "_generate_with_model_fallback", _fake_generate_with_model_fallback)
    items, raw_text = await service.analyze_receipt_image(b"img", "image/jpeg")

    generation_config = captured.get("generation_config")
    assert generation_config is not None
    response_schema = generation_config.response_schema
    assert isinstance(response_schema, dict)
    assert response_schema.get("type") == "object"
    assert items == []
    assert raw_text == "ok"
