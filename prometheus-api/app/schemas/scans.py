from typing import List, Optional

from pydantic import BaseModel, Field

from .common import OperationStatus, ScanStatus
from .inventory import FoodItem


class ScanUploadResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    message: str
    result_status: OperationStatus = OperationStatus.OK
    warnings: List[str] = Field(default_factory=list)


class ScanResultResponse(BaseModel):
    scan_id: str
    status: ScanStatus
    items: List[FoodItem] = Field(default_factory=list)
    raw_text: Optional[str] = None
    error_message: Optional[str] = None
    receipt_store: Optional[str] = None
    receipt_purchased_at: Optional[str] = None
