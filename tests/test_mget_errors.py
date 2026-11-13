"""Missing documents are handled, but programming errors must remain visible."""

from unittest.mock import AsyncMock, Mock

import pytest

from openmock import AsyncFakeOpenSearch, FakeOpenSearch


def test_mget_does_not_hide_unexpected_errors(monkeypatch):
    client = FakeOpenSearch()
    monkeypatch.setattr(client, "get", Mock(side_effect=RuntimeError("broken")))
    with pytest.raises(RuntimeError, match="broken"):
        client.mget(index="books", body={"ids": ["one"]})


@pytest.mark.asyncio
async def test_async_mget_does_not_hide_unexpected_errors(monkeypatch):
    client = AsyncFakeOpenSearch()
    monkeypatch.setattr(client, "get", AsyncMock(side_effect=RuntimeError("broken")))
    with pytest.raises(RuntimeError, match="broken"):
        await client.mget(index="books", body={"ids": ["one"]})
