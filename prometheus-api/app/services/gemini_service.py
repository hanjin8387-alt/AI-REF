import asyncio
import base64
import json
import logging
import time
from typing import List, Optional

import google.generativeai as genai
from google.api_core.exceptions import NotFound
from google.generativeai.types import GenerationConfig

from ..core.config import get_settings
from ..schemas.schemas import FoodItem

logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_SECONDS = 30


class GeminiService:
    """Gemini service for image parsing and recipe generation."""

    def __init__(self):
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.language = settings.default_language
        self._model_candidates = self._build_model_candidates(settings.gemini_model)
        self._active_model_index = 0
        self.model = genai.GenerativeModel(self._model_candidates[self._active_model_index])

    @property
    def _language_instruction(self) -> str:
        lang_map = {"ko": "Korean", "en": "English", "ja": "Japanese"}
        lang_name = lang_map.get(self.language, "Korean")
        return f"Respond in {lang_name}. Use {lang_name} for all ingredient names and text fields."

    @staticmethod
    def _build_model_candidates(configured_model: str) -> list[str]:
        base_candidates = [
            configured_model,
            "gemini-3-flash-preview",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]

        candidates: list[str] = []
        for model in base_candidates:
            name = (model or "").strip()
            if not name:
                continue
            if name.startswith("models/"):
                candidates.extend([name, name.removeprefix("models/")])
            else:
                candidates.extend([name, f"models/{name}"])

        deduplicated: list[str] = []
        for model in candidates:
            name = (model or "").strip()
            if name and name not in deduplicated:
                deduplicated.append(name)
        return deduplicated or ["gemini-3-flash-preview", "models/gemini-3-flash-preview"]

    @staticmethod
    def _is_model_not_found_error(exc: Exception) -> bool:
        if isinstance(exc, NotFound):
            return True
        message = str(exc).lower()
        return "not found for api version" in message or ("model" in message and "not found" in message)

    async def _generate_with_model_fallback(
        self,
        *,
        contents: list[object],
        generation_config: GenerationConfig,
    ):
        last_model_error: Exception | None = None
        for idx in range(self._active_model_index, len(self._model_candidates)):
            model_name = self._model_candidates[idx]
            if idx != self._active_model_index:
                self._active_model_index = idx
                self.model = genai.GenerativeModel(model_name)

            started = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    self.model.generate_content_async(
                        contents=contents,
                        generation_config=generation_config,
                    ),
                    timeout=GEMINI_TIMEOUT_SECONDS,
                )
                elapsed_ms = (time.perf_counter() - started) * 1000
                logger.info("gemini.call model=%s duration_ms=%.2f status=ok", model_name, elapsed_ms)
                return response
            except Exception as exc:
                elapsed_ms = (time.perf_counter() - started) * 1000
                if isinstance(exc, asyncio.TimeoutError):
                    logger.warning(
                        "gemini.call model=%s duration_ms=%.2f status=timeout",
                        model_name,
                        elapsed_ms,
                    )
                else:
                    logger.info(
                        "gemini.call model=%s duration_ms=%.2f status=error",
                        model_name,
                        elapsed_ms,
                    )
                if self._is_model_not_found_error(exc):
                    last_model_error = exc
                    logger.warning("Gemini model unavailable model=%s, trying fallback", model_name)
                    continue
                raise

        if last_model_error:
            raise last_model_error
        raise RuntimeError("No Gemini model candidates configured")

    async def analyze_food_image(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> List[FoodItem]:
        prompt = f"""Identify food items from this image and return JSON only.
{self._language_instruction}

Each item format:
{{
  "name": "ingredient name",
  "quantity": number,
  "unit": "unit",
  "category": "냉장|냉동|상온",
  "confidence": 0.0-1.0
}}

Return an array. If no ingredients are found, return [].
Choose category using practical home storage 기준:
- 냉장: fresh produce, dairy, eggs, opened sauces, refrigerated foods
- 냉동: frozen products, ice cream, frozen meals
- 상온: grains, canned goods, dry foods, unopened shelf-stable items
Do not return any non-JSON text."""

        response = await self._generate_with_model_fallback(
            contents=[
                {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()},
                prompt,
            ],
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        try:
            items_data = json.loads(response.text)
            if not isinstance(items_data, list):
                return []
            return [FoodItem(**item) for item in items_data]
        except Exception:
            logger.warning(
                "analyze_food_image parse failed response_chars=%s preview=%s",
                len(response.text or ""),
                self._response_preview(response.text),
                exc_info=True,
            )
            return []

    async def analyze_receipt_image(
        self, image_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> tuple[List[FoodItem], str | None]:
        prompt = f"""Extract grocery data from this receipt image and return JSON only.
{self._language_instruction}

Response format:
{{
  "raw_text": "best effort OCR text in plain string",
  "items": [
    {{
      "name": "normalized ingredient name",
      "quantity": 1,
      "unit": "unit",
      "category": "냉장|냉동|상온",
      "confidence": 0.0
    }}
  ]
}}

Rules:
- Exclude non-food products.
- If quantity is unclear, use 1.
- If category is unclear, choose the most likely one among 냉장|냉동|상온.
- If OCR text is unclear, set raw_text to null.
- Return items as [] when nothing useful is found.
- Do not return any non-JSON text."""

        response = await self._generate_with_model_fallback(
            contents=[
                {"mime_type": mime_type, "data": base64.b64encode(image_bytes).decode()},
                prompt,
            ],
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        try:
            payload = json.loads(response.text)

            # Backward compatibility: model may still return array.
            if isinstance(payload, list):
                return [FoodItem(**item) for item in payload], None

            if not isinstance(payload, dict):
                return [], None

            items_data = payload.get("items", [])
            raw_text = payload.get("raw_text")

            if not isinstance(items_data, list):
                items_data = []
            if raw_text is not None:
                raw_text = str(raw_text).strip() or None

            return [FoodItem(**item) for item in items_data], raw_text
        except Exception:
            logger.warning(
                "analyze_receipt_image parse failed response_chars=%s preview=%s",
                len(response.text or ""),
                self._response_preview(response.text),
                exc_info=True,
            )
            return [], None

    @staticmethod
    def _coerce_expiry_days(value: object) -> int:
        if value is None:
            return 9999
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return 9999

    @staticmethod
    def _format_expiry_days(value: object) -> str:
        if value is None:
            return "?"
        if isinstance(value, (int, float)):
            return str(int(value))
        text = str(value).strip()
        return text or "?"

    @staticmethod
    def _response_preview(text: str | None, max_chars: int = 180) -> str:
        if not text:
            return "<empty>"
        compact = " ".join(text.split())
        if len(compact) <= max_chars:
            return compact
        return f"{compact[:max_chars]}..."

    async def generate_recipe_recommendations(
        self, inventory_items: List[dict], max_recipes: int = 5
    ) -> List[dict]:
        sorted_items = sorted(
            inventory_items,
            key=lambda x: self._coerce_expiry_days(x.get("expiry_days")),
        )

        items_text = "\n".join(
            [
                f"- {item['name']}: {item.get('quantity', 1)} {item.get('unit', 'unit')} "
                f"(D-{self._format_expiry_days(item.get('expiry_days'))})"
                for item in sorted_items[:20]
            ]
        )

        prompt = f"""Recommend up to {max_recipes} recipes from these ingredients.
Prioritize ingredients that expire sooner.
{self._language_instruction}

Ingredients:
{items_text}

Return JSON array only:
[
  {{
    "id": "recipe_1",
    "title": "recipe title",
    "description": "short description",
    "recommendation_reason": "why this recipe fits current inventory",
    "cooking_time_minutes": 30,
    "difficulty": "easy|medium|hard",
    "servings": 2,
    "ingredients": [{{"name": "item", "quantity": 1, "unit": "unit"}}],
    "instructions": ["step 1", "step 2"],
    "priority_score": 0.95
  }}
]
"""

        response = await self._generate_with_model_fallback(
            contents=[prompt],
            generation_config=GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7,
            ),
        )

        try:
            recipes = json.loads(response.text)
            if isinstance(recipes, list):
                return recipes
            return []
        except Exception:
            logger.warning(
                "generate_recipe_recommendations parse failed response_chars=%s preview=%s",
                len(response.text or ""),
                self._response_preview(response.text),
                exc_info=True,
            )
            return []


_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
