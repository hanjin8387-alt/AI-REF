from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
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
    claim_token: str | None = None


@dataclass(frozen=True)
class IdempotencyExecutionContext:
    db: Client
    device_id: str
    method: str
    path: str
    idempotency_key: str
    request_fingerprint: str
    claim_token: str

    def is_active(self) -> bool:
        row = _load_idempotency_row(
            self.db,
            device_id=self.device_id,
            method=self.method,
            path=self.path,
            idempotency_key=self.idempotency_key,
        )
        return bool(
            row
            and str(row.get("status") or "") == "in_progress"
            and str(row.get("request_fingerprint") or "") == self.request_fingerprint
            and str(row.get("claim_token") or "") == self.claim_token
        )

    def ensure_active(self) -> None:
        if not self.is_active():
            raise IdempotencyLeaseLostError("Idempotency lease lost before side effect.")


class IdempotencyLeaseLostError(RuntimeError):
    """Raised when a stale attempt loses the active lease before mutating state."""


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


def _coerce_row_payload(data: Any) -> dict[str, Any] | None:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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
        claim_token=str(payload.get("claim_token") or "").strip() or None,
    )


def _commit_rpc(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_fingerprint: str,
    claim_token: str,
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
                "p_claim_token": claim_token,
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
    claim_token: str,
    failure_code: str | None,
    failure_message: str | None,
) -> bool:
    try:
        rpc_result = db.rpc(
            IDEMPOTENCY_FAIL_RPC,
            {
                "p_device_id": device_id,
                "p_method": method.upper(),
                "p_path": path,
                "p_idempotency_key": idempotency_key,
                "p_request_fingerprint": request_fingerprint,
                "p_claim_token": claim_token,
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
    return _coerce_bool_result(getattr(rpc_result, "data", None), "fail_idempotency_key")


def _load_idempotency_row(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
) -> dict[str, Any] | None:
    try:
        query_result = (
            db.table(IDEMPOTENCY_TABLE)
            .select(
                "status,request_fingerprint,claim_token,locked_until,response_status,response_headers,response_body"
            )
            .eq("device_id", device_id)
            .eq("method", method.upper())
            .eq("path", path)
            .eq("idempotency_key", idempotency_key)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        if _is_missing_table_error(exc):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Idempotency store is not initialized. Apply migrations first.",
            ) from exc
        raise
    return _coerce_row_payload(getattr(query_result, "data", None))


def _claim_from_row(row: dict[str, Any]) -> IdempotencyClaim:
    locked_until = _parse_timestamp(row.get("locked_until"))
    retry_after_seconds = 0
    if str(row.get("status") or "") == "in_progress" and locked_until is not None:
        retry_after_seconds = max(int((locked_until - datetime.now(timezone.utc)).total_seconds()), 0)
    response_status = row.get("response_status")
    return IdempotencyClaim(
        action=IdempotencyAction.REPLAY if str(row.get("status") or "") == "committed" else IdempotencyAction.IN_PROGRESS,
        status=str(row.get("status") or ""),
        response_status=int(response_status) if response_status is not None else None,
        response_headers=_coerce_headers(row.get("response_headers")),
        response_body=row.get("response_body") if row.get("response_body") is not None else {},
        retry_after_seconds=retry_after_seconds,
        claim_token=str(row.get("claim_token") or "").strip() or None,
    )


def _resolve_superseded_attempt(
    db: Client,
    *,
    device_id: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_fingerprint: str,
) -> JSONResponse:
    row = _load_idempotency_row(
        db,
        device_id=device_id,
        method=method,
        path=path,
        idempotency_key=idempotency_key,
    )
    if not row:
        raise RuntimeError("Idempotency claim was superseded before the winning attempt was recorded.")
    if str(row.get("request_fingerprint") or "") != request_fingerprint:
        _raise_conflict()
    current = _claim_from_row(row)
    if current.status == "committed":
        return _replay_response(current)
    if current.status == "in_progress":
        _raise_in_progress(current.retry_after_seconds)
    raise RuntimeError("Idempotency claim was superseded before a committed result became available.")


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


def _handler_accepts_context(handler: Callable[..., T | Awaitable[T]]) -> bool:
    params = inspect.signature(handler).parameters.values()
    for param in params:
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            return True
    return False


async def _invoke_handler(
    handler: Callable[..., T | Awaitable[T]],
    context: IdempotencyExecutionContext | None = None,
) -> T:
    result = handler(context) if context is not None and _handler_accepts_context(handler) else handler()
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
    handler: Callable[..., T | Awaitable[T]],
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
    claim_token = (claim.claim_token or "").strip()
    if not claim_token:
        raise RuntimeError("Idempotency claim did not return an active claim token.")
    context = IdempotencyExecutionContext(
        db=db,
        device_id=device_id,
        method=method,
        path=path,
        idempotency_key=key,
        request_fingerprint=request_fingerprint,
        claim_token=claim_token,
    )

    try:
        result = await _invoke_handler(handler, context)
        committed = _commit_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            claim_token=claim_token,
            response_status=_response_status(result, default_status_code),
            response_headers=_response_headers(result),
            response_body=_response_payload(result),
            replay_ttl_seconds=replay_ttl_seconds,
        )
        if not committed:
            return _resolve_superseded_attempt(
                db,
                device_id=device_id,
                method=method,
                path=path,
                idempotency_key=key,
                request_fingerprint=request_fingerprint,
            )
        return result
    except HTTPException as exc:
        failed = _fail_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            claim_token=claim_token,
            failure_code=_failure_code_from_http_exception(exc),
            failure_message=_failure_message_from_http_exception(exc),
        )
        if not failed:
            return _resolve_superseded_attempt(
                db,
                device_id=device_id,
                method=method,
                path=path,
                idempotency_key=key,
                request_fingerprint=request_fingerprint,
            )
        raise
    except Exception as exc:
        failed = _fail_rpc(
            db,
            device_id=device_id,
            method=method,
            path=path,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            claim_token=claim_token,
            failure_code="mutation_failed",
            failure_message=str(exc),
        )
        if not failed:
            return _resolve_superseded_attempt(
                db,
                device_id=device_id,
                method=method,
                path=path,
                idempotency_key=key,
                request_fingerprint=request_fingerprint,
            )
        raise
