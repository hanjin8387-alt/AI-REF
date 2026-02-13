import pytest
from fastapi import HTTPException, status

from app.api import admin
from app.core.config import get_settings


def test_require_admin_token_uses_timing_safe_compare(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_compare_digest(left: str, right: str) -> bool:
        calls.append((left, right))
        return True

    monkeypatch.setattr(admin.secrets, "compare_digest", fake_compare_digest)
    admin._require_admin_token("test-app-token")

    assert calls == [("test-app-token", "test-app-token")]


def test_require_admin_token_rejects_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc:
        admin._require_admin_token("invalid-token")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


def test_require_admin_token_rejects_when_server_token_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_TOKEN", "")
    get_settings.cache_clear()

    with pytest.raises(HTTPException) as exc:
        admin._require_admin_token("any-token")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeInventoryTable:
    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages
        self.range_calls: list[tuple[int, int]] = []
        self._current_page = 0

    def select(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def gt(self, *_args, **_kwargs):
        return self

    def range(self, start: int, end: int):
        self.range_calls.append((start, end))
        self._current_page = len(self.range_calls) - 1
        return self

    def execute(self):
        if self._current_page >= len(self.pages):
            return _FakeResult([])
        return _FakeResult(self.pages[self._current_page])


class _FakeDb:
    def __init__(self, table):
        self._table = table

    def table(self, _name: str):
        return self._table


def test_fetch_expiring_inventory_rows_uses_pagination() -> None:
    pages = [
        [{"device_id": "a"}, {"device_id": "b"}],
        [{"device_id": "c"}],
    ]
    table = _FakeInventoryTable(pages)
    db = _FakeDb(table)

    rows = admin._fetch_expiring_inventory_rows(
        db,
        today=admin.datetime.now().date(),
        threshold=admin.datetime.now().date(),
        page_size=2,
    )

    assert rows == pages[0] + pages[1]
    assert table.range_calls == [(0, 1), (2, 3)]


def test_fetch_push_tokens_batches_device_ids() -> None:
    class _FakeDevicesTable:
        def __init__(self) -> None:
            self.calls: list[list[str]] = []

        def select(self, *_args, **_kwargs):
            return self

        def in_(self, _field: str, values: list[str]):
            self.calls.append(list(values))
            self._last_values = list(values)
            return self

        def execute(self):
            return _FakeResult([{"device_id": value, "push_token": f"token-{value}"} for value in self._last_values])

    devices_table = _FakeDevicesTable()
    db = _FakeDb(devices_table)
    tokens = admin._fetch_push_tokens(
        db,
        device_ids=["d1", "d2", "d3", "d4", "d5"],
        page_size=2,
    )

    assert devices_table.calls == [["d1", "d2"], ["d3", "d4"], ["d5"]]
    assert tokens["d1"] == "token-d1"
    assert tokens["d5"] == "token-d5"
