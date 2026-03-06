from enum import Enum


class ScanSourceType(str, Enum):
    CAMERA = "camera"
    GALLERY = "gallery"
    RECEIPT = "receipt"


class ScanStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationType(str, Enum):
    INVENTORY = "inventory"
    COOKING = "cooking"
    EXPIRY = "expiry"
    SYSTEM = "system"


class OperationStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
