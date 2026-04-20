import pytest
from openmock import AsyncFakeOpenSearch


@pytest.mark.asyncio
async def test_aliases():
    client = AsyncFakeOpenSearch()
    await client.indices.create(index="test-index")

    await client.indices.put_alias(index="test-index", name="test-alias")

    aliases = await client.indices.get_alias(index="test-index")
    assert "test-alias" in aliases["test-index"]["aliases"]

    await client.indices.delete_alias(index="test-index", name="test-alias")
    aliases = await client.indices.get_alias(index="test-index")
    assert "test-alias" not in aliases["test-index"]["aliases"]


@pytest.mark.asyncio
async def test_stats():
    client = AsyncFakeOpenSearch()
    await client.indices.create(index="test-index")

    response = await client.indices.stats(index="test-index")
    assert "_shards" in response
    assert "test-index" in response["indices"]
