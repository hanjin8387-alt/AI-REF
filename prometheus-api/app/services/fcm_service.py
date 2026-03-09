"""Firebase Cloud Messaging service for push notifications."""
import json
import logging
from typing import Optional

from ..core.config import get_settings

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _ensure_firebase() -> bool:
    """Initialize Firebase Admin SDK if not yet done. Returns True on success."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    settings = get_settings()
    if not settings.firebase_credentials:
        logger.debug("firebase_credentials not configured — push disabled")
        return False

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_initialized = True
            return True

        cred_data = json.loads(settings.firebase_credentials)
        cred = credentials.Certificate(cred_data)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        logger.info("Firebase Admin SDK initialized")
        return True
    except Exception:
        logger.exception("Firebase Admin SDK initialization failed")
        return False


def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> bool:
    """Send a single push notification via FCM. Returns True on success."""
    if not _ensure_firebase():
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=push_token,
        )
        messaging.send(message)
        logger.info("FCM sent to token=%s...%s", push_token[:8], push_token[-4:])
        return True
    except Exception:
        logger.exception("FCM send failed token=%s...%s", push_token[:8], push_token[-4:])
        return False


def send_push_to_many(
    push_tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict] = None,
) -> int:
    """Send push notification to multiple tokens. Returns count of successes."""
    if not push_tokens or not _ensure_firebase():
        return 0

    try:
        from firebase_admin import messaging

        messages = [
            messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in (data or {}).items()},
                token=token,
            )
            for token in push_tokens
        ]

        response = messaging.send_each(messages)
        success_count = sum(1 for r in response.responses if r.success)
        logger.info("FCM batch: %d/%d sent", success_count, len(push_tokens))
        return success_count
    except Exception:
        logger.exception("FCM batch send failed")
        return 0
