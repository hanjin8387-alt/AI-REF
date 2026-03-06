from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, Field

from .common import OperationStatus


class BackupRestoreRequest(BaseModel):
    payload: dict[str, Any]
    mode: str = Field(default="merge", description="merge | replace")


class BackupTableResult(BaseModel):
    table: str
    status: OperationStatus
    row_count: int = 0
    error: str | None = None


class BackupRestoreResponse(BaseModel):
    success: bool
    message: str
    status: OperationStatus = OperationStatus.OK
    warnings: List[str] = Field(default_factory=list)
    restored_counts: dict[str, int] = Field(default_factory=dict)
    table_results: List[BackupTableResult] = Field(default_factory=list)


class BackupExportResponse(BaseModel):
    success: bool
    exported_at: datetime
    status: OperationStatus = OperationStatus.OK
    warnings: List[str] = Field(default_factory=list)
    table_results: List[BackupTableResult] = Field(default_factory=list)
    payload: dict[str, Any]
