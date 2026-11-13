"""Contract tests run unchanged against raw real and fake clients."""

import inspect
import uuid

import opensearchpy
import pytest
import pytest_asyncio
from opensearchpy.exceptions import RequestError

from openmock import AsyncFakeOpenSearch, FakeOpenSearch
from tests.backend import get_test_hosts, using_real_opensearch


async def call(method, **kwargs):
    result = method(**kwargs)
    return await result if inspect.isawaitable(result) else result


@pytest_asyncio.fixture(params=[False, True], ids=["sync", "async"])
async def client_index(request):
    if using_real_opensearch():
        cls = opensearchpy.AsyncOpenSearch if request.param else opensearchpy.OpenSearch
    else:
        cls = AsyncFakeOpenSearch if request.param else FakeOpenSearch
    client = cls(hosts=get_test_hosts())
    index = f"maintenance-{uuid.uuid4().hex}"
    await call(
        client.indices.create,
        index=index,
        body={
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "rank": {"type": "integer"},
                    "group": {"type": "keyword"},
                }
            },
        },
    )
    try:
        yield client, index
    finally:
        await call(client.indices.delete, index=index)
        await call(client.close)


async def seed(client, index, count=15):
    for n in range(count):
        await call(
            client.index,
            index=index,
            id=str(n),
            body={"rank": n, "group": "even" if n % 2 == 0 else "odd"},
        )
    await call(client.indices.refresh, index=index)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body,params,expected",
    [
        ({}, {}, list(range(10))),
        ({"from": 3}, {}, list(range(3, 13))),
        ({"from": 1, "size": 2}, {"from": 5, "size": 3}, [5, 6, 7]),
        ({"size": 0}, {}, []),
    ],
)
async def test_pagination(client_index, body, params, expected):
    client, index = client_index
    await seed(client, index)
    response = await call(
        client.search,
        index=index,
        body={"sort": [{"rank": {"order": "asc"}}], **body},
        params=params,
    )
    assert [hit["_source"]["rank"] for hit in response["hits"]["hits"]] == expected
    assert response["hits"]["total"]["value"] == 15
    assert (await call(client.count, index=index))["count"] == 15


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort",
    [[{"group": "asc"}, {"rank": "desc"}], ["group", {"rank": {"order": "desc"}}]],
)
async def test_multifield_sort_and_missing_last(client_index, sort):
    client, index = client_index
    for doc_id, body in [
        ("a", {"group": "a", "rank": 1}),
        ("b", {"group": "a", "rank": 3}),
        ("c", {"group": "a"}),
        ("d", {"group": "b", "rank": 9}),
    ]:
        await call(client.index, index=index, id=doc_id, body=body)
    await call(client.indices.refresh, index=index)
    response = await call(client.search, index=index, body={"sort": sort})
    assert [hit["_id"] for hit in response["hits"]["hits"]] == ["b", "a", "c", "d"]


@pytest.mark.asyncio
async def test_scroll_body_size_reaches_all_documents(client_index):
    client, index = client_index
    await seed(client, index)
    response = await call(
        client.search,
        index=index,
        body={"size": 4, "sort": ["rank"]},
        params={"scroll": "1m"},
    )
    ids = []
    for _ in range(5):
        hits = response["hits"]["hits"]
        if not hits:
            break
        ids.extend(hit["_id"] for hit in hits)
        response = await call(
            client.scroll, scroll_id=response["_scroll_id"], params={"scroll": "1m"}
        )
    assert ids == [str(n) for n in range(15)]


@pytest.mark.asyncio
async def test_delete_by_query_exceeds_search_page(client_index):
    client, index = client_index
    await seed(client, index)
    response = await call(
        client.delete_by_query,
        index=index,
        body={"query": {"match_all": {}}},
        params={"refresh": "true"},
    )
    assert response["deleted"] == 15
    assert (await call(client.count, index=index))["count"] == 0


@pytest.mark.asyncio
async def test_search_response_does_not_mutate_stored_source(client_index):
    client, index = client_index
    await seed(client, index, 1)
    response = await call(client.search, index=index)
    response["hits"]["hits"][0]["_source"]["rank"] = 99
    assert (await call(client.get, index=index, id="0"))["_source"]["rank"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["from", "size"])
async def test_negative_pagination_rejected(client_index, field):
    client, index = client_index
    with pytest.raises(RequestError):
        await call(client.search, index=index, body={field: -1})


@pytest.mark.asyncio
@pytest.mark.parametrize("write", ["index", "create"])
async def test_document_input_and_get_response_are_copied(client_index, write):
    client, index = client_index
    body = {"nested": {"value": 1}}
    await call(getattr(client, write), index=index, id="one", body=body)
    body["nested"]["value"] = 2
    loaded = await call(client.get, index=index, id="one")
    assert loaded["_source"]["nested"]["value"] == 1
    loaded["_source"]["nested"]["value"] = 3
    assert (await call(client.get, index=index, id="one"))["_source"]["nested"][
        "value"
    ] == 1


@pytest.mark.asyncio
async def test_update_by_query_exceeds_search_page(client_index):
    client, index = client_index
    await seed(client, index)
    result = await call(
        client.update_by_query,
        index=index,
        body={
            "query": {"match_all": {}},
            "script": {
                "source": "ctx._source.group = params.group",
                "params": {"group": "updated"},
            },
        },
        params={"refresh": "true"},
    )
    assert result["updated"] == 15
    assert (
        await call(
            client.count, index=index, body={"query": {"term": {"group": "updated"}}}
        )
    )["count"] == 15
