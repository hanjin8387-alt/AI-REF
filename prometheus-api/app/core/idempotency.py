from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from supabase import Client

IDEMPOTENCY_TABLE = "idempotency_keys"
IDEMPOTENCY_CLAIM_RPC = "claim_idempotency_key"
IDEMPOTENCY_COMMIT_RPC = "commit_idempotency_key"
IDEMPOTENCY_FAIL_RPC = "fail_idempotency_key"
IDEMPOTENCY_LOCK_TTL_SECONDS = 120
IDEMPOTENCY_REPLAY_TTL_SECONDS = 24 * 60 * 60
IDEMPOTENCY_REPLAY_HEADER = "X-Idempotency-Replayed"
IDEMPOTENCY_STATUS_HEADER = "X-Idempotency-Status"
IDEMPOTENCY_REQUIRED_DETAIL = "X-Idempotency-Key header is required."
T = TypeVar("T")


class IdempotencyAction(str, Enum):
    STARTED = "started"
    REPLAY = "replay"
    IN_PROGRESS = "in_progress"
    CONFLICT = "conflict"


@dataclass
class IdempotencyClaim:
    action: IdempotencyAction
    status: str
    response_status: int | None
    response_headers: dict[str, str]
    response_body: Any
    retry_after_seconds: int


def _is_missing_table_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "pgrst205" in text and IDEMPOTENCY_TABLE in text


def _normalize_json(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _normalize_json(value.model_dump(mode="json"))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _normalize_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_json(item) for item in value]
    return value


def build_request_fingerprint(payload: Any) -> str:
    normalized = _normalize_json(payload)
    encoded = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return sha256(encoded.encode("utf-8")).hexdigest()


def _coerce_headers(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    headers: dict[str, str] = {}
    for key, item in value.items():
        if key and item is not None:
            headers[str(key)] = str(item)
    return headers


def _coerce_claim_payload(data: Any) -> dict[str, Any]:
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
        return {}
    if isinstance(data, dict):
        return data
    return {}


def _coerce_bool_result(data: Any, function_name: str) -> bool:
    if isinstance(data, bool):
        return data
    if isinstance(data, list):
        for item in data:
            if isinstance(item, bool):
                return item
            if isinstance(item, dict):
                if function_name in item:
                    return bool(item.get(function_name))
                for value in item.values():
                    if isinstance(value, bool):
                        return value
        return False
    if isinstance(data, dict):
        if function_name in data:
            return bool(data.get(function_name))
        for value in data.values():
            if isinstance(value, bool):
                return value
    return bool(data)


def _claim_rpc(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_fingerprint: str,
    lock_ttl_seconds: int,
    replay_ttl_seconds: int,
) -> IdempotencyClaim:
    try:
        rpc_result = db.rpc(
            IDEMPOTENCY_CLAIM_RPC,
            {
                "p_device_id": device_id,
                "p_method": method.upper(),
                "p_path": path,
                "p_idempotency_key": idempotency_key,
                "p_request_fingerprint": request_fingerprint,
                "p_lock_ttl_seconds": lock_ttl_seconds,
                "p_replay_ttl_seconds": replay_ttl_seconds,
            },
        ).execute()
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise

    payload = _coerce_claim_payload(getattr(rpc_result, "data", None))
    action_raw = str(payload.get("action") or "").strip() or IdempotencyAction.STARTED.value
    response_status = payload.get("response_status")
    return IdempotencyClaim(
        action=IdempotencyAction(action_raw),
        status=str(payload.get("status") or ""),
        response_status=int(response_status) if response_status is not None else None,
        response_headers=_coerce_headers(payload.get("response_headers")),
        response_body=payload.get("response_body") if payload.get("response_body") is not None else {},
        retry_after_seconds=max(int(payload.get("retry_after_seconds") or 0), 0),
    )


def _commit_rpc(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_fingerprint: str,
    response_status: int,
    response_headers: dict[str, str],
    response_body: Any,
    replay_ttl_seconds: int,
) -> bool:
    try:
        rpc_result = db.rpc(
            IDEMPOTENCY_COMMIT_RPC,
            {
                "p_device_id": device_id,
                "p_method": method.upper(),
                "p_path": path,
                "p_idempotency_key": idempotency_key,
                "p_request_fingerprint": request_fingerprint,
                "p_response_status": int(response_status),
                "p_response_headers": _normalize_json(response_headers),
                "p_response_body": _normalize_json(response_body),
                "p_replay_ttl_seconds": replay_ttl_seconds,
            },
        ).execute()
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise

    return _coerce_bool_result(getattr(rpc_result, "data", None), "commit_idempotency_key")


def _fail_rpc(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_fingerprint: str,
    failure_code: str | None,
    failure_message: str | None,
) -> None:
    try:
        db.rpc(
            IDEMPOTENCY_FAIL_RPC,
            {
                "p_device_id": device_id,
                "p_method": method.upper(),
                "p_path": path,
                "p_idempotency_key": idempotency_key,
                "p_request_fingerprint": request_fingerprint,
                "p_failure_code": failure_code,
                "p_failure_message": failure_message,
            },
        ).execute()
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise


def _replay_response(claim: IdempotencyClaim) -> JSONResponse:
    headers = dict(claim.response_headers)
    headers[IDEMPOTENCY_REPLAY_HEADER] = "true"
    headers[IDEMPOTENCY_STATUS_HEADER] = IdempotencyAction.REPLAY.value
    return JSONResponse(
        status_code=int(claim.response_status or status.HTTP_200_OK),
        content=claim.response_body,
        headers=headers,
    )


def _raise_in_progress(retry_after_seconds: int) -> None:
    retry_after = max(int(retry_after_seconds or 0), 1)
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "idempotency_in_progress",
            "message": "A matching request is already in progress.",
        },
        headers={
            "Retry-After": str(retry_after),
            IDEMPOTENCY_STATUS_HEADER: IdempotencyAction.IN_PROGRESS.value,
        },
    )


def _raise_conflict() -> None:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "idempotency_key_conflict",
            "message": "The idempotency key is already associated with a different request payload.",
        },
        headers={IDEMPOTENCY_STATUS_HEADER: IdempotencyAction.CONFLICT.value},
    )


def _response_payload(result: Any) -> Any:
    if isinstance(result, BaseModel):
        return result.model_dump(mode="json")
    if isinstance(result, JSONResponse):
        body = result.body.decode("utf-8") if result.body else "{}"
        return json.loads(body or "{}")
    if isinstance(result, Response):
        body = result.body.decode("utf-8") if result.body else "{}"
        if result.media_type == "application/json":
            return json.loads(body or "{}")
        return {"body": body}
    return _normalize_json(result)


def _response_status(result: Any, default_status: int) -> int:
    if isinstance(result, Response):
        return int(result.status_code)
    return int(default_status)


def _response_headers(result: Any) -> dict[str, str]:
    if not isinstance(result, Response):
        return {}
    headers = {key: value for key, value in result.headers.items() if key.lower() != IDEMPOTENCY_REPLAY_HEADER.lower()}
    headers.pop(IDEMPOTENCY_STATUS_HEADER, None)
    return headers


async def _invoke_handler(handler: Callable[[], T | Awaitable[T]]) -> T:
    result = handler()
    if inspect.isawaitable(result):
        return await result
    return result


def _failure_code_from_http_exception(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        code = detail.get("code")
        if code:
            return str(code)
    return f"http_{exc.status_code}"


def _failure_message_from_http_exception(exc: HTTPException) -> str:
    detail = exc.detail
    if isinstance(detail, dict):
        message = detail.get("message")
        if message:
            return str(message)
    return str(detail)


async def execute_idempotent_mutation(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str | None,
    request_payload: Any,
    handler: Callable[[], T | Awaitable[T]],
    require_key: bool = False,
    default_status_code: int = status.HTTP_200_OK,
    lock_ttl_seconds: int = IDEMPOTENCY_LOCK_TTL_SECONDS,
    replay_ttl_seconds: int = IDEMPOTENCY_REPLAY_TTL_SECONDS,
) -> T | JSONResponse:
    key = (idempotency_key or "").strip()
    if not key:
        if require_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=IDEMPOTENCY_REQUIRED_DETAIL)
        return await _invoke_handler(handler)

    request_fingerprint = build_request_fingerprint(request_payload)
    claim = _claim_rpc(
        db,
        device_id=device_id,
        method=method,
        path=path,
        idempotency_key=key,
        request_fingerprint=request_fingerprint,
        lock_ttl_seconds=lock_ttl_seconds,
        replay_ttl_seconds=replay_ttl_seconds,
    )

    if claim.action == IdempotencyAction.REPLAY:
        return _replay_response(claim)
    if claim.action == IdempotencyAction.IN_PROGRESS:
        _raise_in_progress(claim.retry_after_seconds)
    if claim.action == IdempotencyAction.CONFLICT:
        _raise_conflict()

    try:
        result = await _invoke_handler(handler)
        committed = _commit_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            response_status=_response_status(result, default_status_code),
            response_headers=_response_headers(result),
            response_body=_response_payload(result),
            replay_ttl_seconds=replay_ttl_seconds,
        )
        if not committed:
            raise RuntimeError("Idempotency commit failed.")
        return result
    except HTTPException as exc:
        _fail_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            failure_code=_failure_code_from_http_exception(exc),
            failure_message=_failure_message_from_http_exception(exc),
        )
        raise
    except Exception as exc:
        _fail_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            failure_code="mutation_failed",
            failure_message=str(exc),
        )
        raise
