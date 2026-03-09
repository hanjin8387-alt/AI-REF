import asyncio
import json
import logging
import time
from typing import Any, List, Literal, Optional

from google import genai
from google.genai import types
from google.genai.errors import ClientError
from pydantic import BaseModel, ValidationError

from ..core.config import get_settings
from ..core.units import DEFAULT_UNIT
from ..schemas.inventory import FoodItem

logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_SECONDS = 30

FOOD_ITEM_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "quantity": {"type": "number"},
        "unit": {"type": "string"},
        "category": {"type": ["string", "null"], "enum": ["냉장", "냉동", "상온", None]},
        "confidence": {"type": "number"},
        "unit_price": {"type": ["number", "null"]},
        "total_price": {"type": ["number", "null"]},
        "currency": {"type": ["string", "null"]},
    },
    "required": ["name"],
}
FOOD_ITEMS_JSON_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": FOOD_ITEM_JSON_SCHEMA,
}
RECEIPT_ANALYSIS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "raw_text": {"type": ["string", "null"]},
        "items": FOOD_ITEMS_JSON_SCHEMA,
    },
    "required": ["items"],
}
RECIPE_INGREDIENT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "name": {"type": "string"},
        "quantity": {"type": "number"},
        "unit": {"type": "string"},
    },
    "required": ["name"],
}
RECIPE_RECOMMENDATION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "recommendation_reason": {"type": ["string", "null"]},
        "cooking_time_minutes": {"type": "integer"},
        "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
        "servings": {"type": "integer"},
        "ingredients": {"type": "array", "items": RECIPE_INGREDIENT_JSON_SCHEMA},
        "instructions": {"type": "array", "items": {"type": "string"}},
        "priority_score": {"type": "number"},
    },
    "required": ["id", "title", "description", "ingredients", "instructions"],
}
RECIPE_RECOMMENDATIONS_JSON_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": RECIPE_RECOMMENDATION_JSON_SCHEMA,
}


class GeminiContractError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ReceiptAnalysisPayload(BaseModel):
    raw_text: str | None = None
    items: list[FoodItem] = []


class GeneratedRecipeIngredientPayload(BaseModel):
    name: str
    quantity: float = 1
    unit: str = DEFAULT_UNIT


class GeneratedRecipePayload(BaseModel):
    id: str
    title: str
    description: str
    recommendation_reason: str | None = None
    cooking_time_minutes: int = 30
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    servings: int = 2
    ingredients: list[GeneratedRecipeIngredientPayload] = []
    instructions: list[str] = []
    priority_score: float = 0.5


class GeminiService:
    """Gemini service for image parsing and recipe generation."""

    def __init__(self):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self.language = settings.default_language
        self._model_candidates = self._build_model_candidates(settings.gemini_model)
        self._active_model_index = 0

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
        if isinstance(exc, ClientError):
            status = getattr(exc, "status", None)
            if status is not None and getattr(status, "code", None) == 404:
                return True
        message = str(exc).lower()
        return "not found for api version" in message or ("model" in message and "not found" in message)

    async def _generate_with_model_fallback(
        self,
        *,
        contents: list[object],
        generation_config: types.GenerateContentConfig,
    ):
        last_model_error: Exception | None = None
        for idx in range(self._active_model_index, len(self._model_candidates)):
            model_name = self._model_candidates[idx]
            if idx != self._active_model_index:
                self._active_model_index = idx

            started = time.perf_counter()
            try:
                response = await asyncio.wait_for(
                    self._client.aio.models.generate_content(
                        model=model_name,
                        contents=contents,
                        config=generation_config,
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

    def _load_json_payload(self, *, response_text: str | None, context: str) -> object:
        if not response_text:
            raise GeminiContractError("empty_response", f"Gemini {context} returned an empty response.")
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "%s parse failed response_chars=%s preview=%s",
                context,
                len(response_text or ""),
                self._response_preview(response_text),
                exc_info=True,
            )
            raise GeminiContractError("invalid_json", f"Gemini {context} returned invalid JSON.") from exc

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
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            generation_config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FOOD_ITEMS_JSON_SCHEMA,
                temperature=0.2,
            ),
        )

        items_data = self._load_json_payload(
            response_text=getattr(response, "text", None),
            context="food analysis",
        )

        if not isinstance(items_data, list):
            raise GeminiContractError("invalid_shape", "Gemini food analysis payload must be a JSON array.")

        try:
            return [FoodItem(**item) for item in items_data]
        except ValidationError as exc:
            logger.warning(
                "analyze_food_image schema failed response_chars=%s preview=%s",
                len(response.text or ""),
                self._response_preview(response.text),
                exc_info=True,
            )
            raise GeminiContractError("schema_validation_failed", "Gemini food analysis payload failed schema validation.") from exc

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
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt,
            ],
            generation_config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RECEIPT_ANALYSIS_JSON_SCHEMA,
                temperature=0.1,
            ),
        )

        payload = self._load_json_payload(
            response_text=getattr(response, "text", None),
            context="receipt analysis",
        )

        if not isinstance(payload, dict):
            raise GeminiContractError("invalid_shape", "Gemini receipt analysis payload must be a JSON object.")

        try:
            parsed_payload = ReceiptAnalysisPayload(**payload)
        except ValidationError as exc:
            logger.warning(
                "analyze_receipt_image schema failed response_chars=%s preview=%s",
                len(response.text or ""),
                self._response_preview(response.text),
                exc_info=True,
            )
            raise GeminiContractError("schema_validation_failed", "Gemini receipt payload failed schema validation.") from exc

        raw_text = parsed_payload.raw_text
        if raw_text is not None:
            raw_text = str(raw_text).strip() or None
        return parsed_payload.items, raw_text

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
            generation_config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RECIPE_RECOMMENDATIONS_JSON_SCHEMA,
                temperature=0.7,
            ),
        )

        recipes = self._load_json_payload(
            response_text=getattr(response, "text", None),
            context="recipe recommendation",
        )

        if not isinstance(recipes, list):
            raise GeminiContractError("invalid_shape", "Gemini recipe response must be a JSON array.")
        try:
            parsed_recipes = [GeneratedRecipePayload(**recipe) for recipe in recipes]
        except ValidationError as exc:
            logger.warning(
                "generate_recipe_recommendations schema failed response_chars=%s preview=%s",
                len(getattr(response, "text", "") or ""),
                self._response_preview(getattr(response, "text", None)),
                exc_info=True,
            )
            raise GeminiContractError("schema_validation_failed", "Gemini recipe payload failed schema validation.") from exc
        return [recipe.model_dump(mode="json") for recipe in parsed_recipes]


_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiService()
    return _gemini_service
