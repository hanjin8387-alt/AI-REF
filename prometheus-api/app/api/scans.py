import logging
import os
import re
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from supabase import Client

from ..core.config import get_settings
from ..core.db_columns import SCAN_SELECT_COLUMNS
from ..core.database import get_db
from ..core.security import get_device_id, require_app_token
from ..schemas.schemas import (
    BarcodeProductInfo,
    BarcodeResponse,
    FoodItem,
    ScanResultResponse,
    ScanSourceType,
    ScanStatus,
    ScanUploadResponse,
)
from ..services.gemini_service import GeminiService, get_gemini_service
from ..services.storage_utils import STORAGE_CATEGORIES, guess_storage_from_name, normalize_storage_category

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
MAX_SCAN_FILENAME_LENGTH = 255
DEFAULT_SCAN_FILENAME = "scan-upload"

router = APIRouter(
    prefix="/scans",
    tags=["scans"],
    dependencies=[Depends(require_app_token)],
)

def _normalize_unit(value: str | None) -> str:
    unit = (value or "").strip()
    if not unit:
        return "개"
    if unit.lower() == "unit":
        return "개"
    return unit


def _enrich_scan_items_with_storage(items: list[FoodItem]) -> list[FoodItem]:
    enriched: list[FoodItem] = []
    for item in items:
        normalized = normalize_storage_category(item.category)
        if normalized is None:
            normalized = guess_storage_from_name(item.name)
        if normalized not in STORAGE_CATEGORIES:
            normalized = "상온"
        enriched.append(
            item.model_copy(
                update={
                    "category": normalized,
                    "unit": _normalize_unit(item.unit),
                }
            )
        )
    return enriched


def _normalize_original_filename(filename: str | None) -> str:
    if not filename:
        return DEFAULT_SCAN_FILENAME

    cleaned = os.path.basename(filename).strip()
    cleaned = "".join(ch for ch in cleaned if ch.isprintable())
    if not cleaned:
        return DEFAULT_SCAN_FILENAME

    if len(cleaned) <= MAX_SCAN_FILENAME_LENGTH:
        return cleaned

    stem, ext = os.path.splitext(cleaned)
    ext = ext[:32]
    allowed_stem_len = max(1, MAX_SCAN_FILENAME_LENGTH - len(ext))
    truncated = f"{stem[:allowed_stem_len]}{ext}"
    return truncated[:MAX_SCAN_FILENAME_LENGTH]


def _is_filename_too_long_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "22001" in text or ("value too long" in text and "character varying" in text)


def _extract_receipt_metadata(raw_text: str | None) -> tuple[str | None, str | None]:
    if not raw_text:
        return None, None

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    store_name = lines[0][:120] if lines else None

    patterns = [
        r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})",
        r"(\d{2})[./-](\d{1,2})[./-](\d{1,2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_text)
        if not match:
            continue
        parts = [int(value) for value in match.groups()]
        try:
            if len(parts[0].__str__()) == 2 and parts[0] < 100:  # yy-mm-dd
                year = 2000 + parts[0]
                month = parts[1]
                day = parts[2]
            else:
                year, month, day = parts
            parsed = datetime(year, month, day)
            return store_name, parsed.date().isoformat()
        except Exception:
            continue

    return store_name, None


def _safe_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    text = raw.replace(",", "").strip()
    try:
        value = float(text)
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


def _extract_item_prices(items: list[FoodItem], raw_text: str | None) -> list[FoodItem]:
    if not raw_text:
        return items

    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return items

    price_pattern = re.compile(r"((?:\d{1,3}(?:,\d{3})+)|\d+)(?:\s*원|\s*krw)?", re.IGNORECASE)
    line_cache = [(line.lower().replace(" ", ""), line) for line in lines]

    enriched: list[FoodItem] = []
    for item in items:
        item_key = item.name.lower().replace(" ", "")
        matched_price: float | None = None
        for compact, original in line_cache:
            if item_key and item_key not in compact:
                continue
            numbers = [m.group(1) for m in price_pattern.finditer(original)]
            if not numbers:
                continue
            parsed_numbers = [_safe_amount(value) for value in numbers]
            parsed_numbers = [value for value in parsed_numbers if value is not None]
            if not parsed_numbers:
                continue
            matched_price = max(parsed_numbers)
            break

        if matched_price is None:
            enriched.append(item)
            continue

        enriched.append(
            item.model_copy(
                update={
                    "unit_price": matched_price,
                    "total_price": matched_price,
                    "currency": "KRW",
                }
            )
        )

    return enriched


def _persist_price_history(
    db: Client,
    *,
    device_id: str,
    scan_id: str,
    source_type: ScanSourceType,
    items: list[FoodItem],
    store_name: str | None,
    purchased_on: str | None,
) -> None:
    rows = []
    for item in items:
        unit_price = item.unit_price if item.unit_price is not None else item.total_price
        if unit_price is None:
            continue
        rows.append(
            {
                "device_id": device_id,
                "scan_id": scan_id,
                "item_name": item.name,
                "unit_price": round(float(unit_price), 2),
                "currency": item.currency or "KRW",
                "store_name": store_name,
                "purchased_on": purchased_on,
                "source_type": source_type.value,
            }
        )

    if not rows:
        return

    try:
        db.table("price_history").insert(rows).execute()
    except Exception:
        logger.warning("price_history insert skipped (table missing or insert failed)", exc_info=True)


@router.post("/upload", response_model=ScanUploadResponse)
@limiter.limit("10/minute")
async def upload_scan(
    request: Request,
    file: UploadFile = File(...),
    source_type: ScanSourceType = ScanSourceType.CAMERA,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
    gemini: GeminiService = Depends(get_gemini_service),
):
    settings = get_settings()
    scan_id = str(uuid.uuid4())

    try:
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="이미지 파일만 업로드할 수 있습니다.",
            )

        mime_type = file.content_type or "image/jpeg"
        max_upload_bytes = settings.max_upload_size_mb * 1024 * 1024
        chunks: list[bytes] = []
        total_size = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total_size += len(chunk)
            if total_size > max_upload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"이미지 용량이 너무 큽니다. 최대 {settings.max_upload_size_mb}MB까지 지원합니다.",
                )
            chunks.append(chunk)
        image_bytes = b"".join(chunks)

        original_filename = _normalize_original_filename(file.filename)

        scan_row = {
            "id": scan_id,
            "device_id": device_id,
            "source_type": source_type.value,
            "status": ScanStatus.PROCESSING.value,
            "original_filename": original_filename,
        }
        try:
            db.table("scans").insert(scan_row).execute()
        except Exception as insert_exc:
            if not _is_filename_too_long_error(insert_exc):
                raise
            logger.warning("scan filename exceeded DB column length; retrying with fallback filename")
            scan_row["original_filename"] = DEFAULT_SCAN_FILENAME
            db.table("scans").insert(scan_row).execute()

        raw_text = None
        if source_type == ScanSourceType.RECEIPT:
            items, raw_text = await gemini.analyze_receipt_image(image_bytes, mime_type)
        else:
            items = await gemini.analyze_food_image(image_bytes, mime_type)

        items = _extract_item_prices(_enrich_scan_items_with_storage(items), raw_text)
        receipt_store, receipt_purchased_on = _extract_receipt_metadata(raw_text)

        db.table("scans").update(
            {
                "status": ScanStatus.COMPLETED.value,
                "items": [item.model_dump(mode="json") for item in items],
                "raw_text": raw_text,
            }
        ).eq("id", scan_id).eq("device_id", device_id).execute()

        if source_type == ScanSourceType.RECEIPT:
            _persist_price_history(
                db,
                device_id=device_id,
                scan_id=scan_id,
                source_type=source_type,
                items=items,
                store_name=receipt_store,
                purchased_on=receipt_purchased_on,
            )

        return ScanUploadResponse(
            scan_id=scan_id,
            status=ScanStatus.COMPLETED,
            message=f"{len(items)}개 항목을 감지했어요.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("scan upload failed scan_id=%s device_id=%s", scan_id, device_id)
        db.table("scans").update(
            {
                "status": ScanStatus.FAILED.value,
                "error_message": "스캔 처리에 실패했어요.",
            }
        ).eq("id", scan_id).eq("device_id", device_id).execute()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="스캔 분석에 실패했습니다.",
        ) from exc


@router.get("/{scan_id}/result", response_model=ScanResultResponse)
async def get_scan_result(
    scan_id: str,
    device_id: str = Depends(get_device_id),
    db: Client = Depends(get_db),
):
    result = (
        db.table("scans")
        .select(SCAN_SELECT_COLUMNS)
        .eq("id", scan_id)
        .eq("device_id", device_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스캔 결과를 찾을 수 없습니다.")

    scan = result.data
    items = [FoodItem(**item) for item in (scan.get("items") or [])]
    items = _enrich_scan_items_with_storage(items)
    receipt_store, receipt_purchased_at = _extract_receipt_metadata(scan.get("raw_text"))

    return ScanResultResponse(
        scan_id=scan_id,
        status=ScanStatus(scan.get("status", "pending")),
        items=items,
        raw_text=scan.get("raw_text"),
        error_message=scan.get("error_message"),
        receipt_store=receipt_store,
        receipt_purchased_at=receipt_purchased_at,
    )


@router.get("/barcode", response_model=BarcodeResponse)
@limiter.limit("20/minute")
async def lookup_barcode(
    request: Request,
    code: str = Query(..., min_length=4, max_length=20, description="Barcode string (EAN-13, etc.)"),
    device_id: str = Depends(get_device_id),
):
    """Look up a product by barcode using Open Food Facts API."""
    settings = get_settings()
    if not settings.open_food_facts_enabled:
        return BarcodeResponse(found=False, barcode=code)

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"https://world.openfoodfacts.org/api/v2/product/{code}.json",
                params={"fields": "product_name,categories_tags,image_url"},
            )

        if resp.status_code != 200:
            return BarcodeResponse(found=False, barcode=code)

        data = resp.json()
        product_data = data.get("product")
        if not product_data or data.get("status") != 1:
            return BarcodeResponse(found=False, barcode=code)

        name = product_data.get("product_name", "").strip()
        if not name:
            return BarcodeResponse(found=False, barcode=code)

        categories = product_data.get("categories_tags") or []
        category = None
        if categories:
            raw_cat = categories[0].replace("en:", "").replace("-", " ")
            category = raw_cat.title()

        expiry_map = {
            "dairy": 14,
            "milk": 7,
            "yogurt": 14,
            "cheese": 30,
            "meat": 5,
            "poultry": 5,
            "fish": 3,
            "seafood": 3,
            "bread": 5,
            "bakery": 5,
            "fruit": 7,
            "vegetable": 7,
            "produce": 7,
            "frozen": 90,
            "canned": 365,
            "beverage": 180,
        }
        suggested_days = None
        cat_lower = (category or "").lower()
        for key, days in expiry_map.items():
            if key in cat_lower:
                suggested_days = days
                break

        return BarcodeResponse(
            found=True,
            barcode=code,
            product=BarcodeProductInfo(
                name=name,
                category=category,
                suggested_expiry_days=suggested_days,
                image_url=product_data.get("image_url"),
            ),
        )
    except Exception:
        logger.exception("barcode lookup failed code=%s", code)
        return BarcodeResponse(found=False, barcode=code)
