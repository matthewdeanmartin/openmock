import uuid

import pytest
from openmock import openmock
import opensearchpy
import opensearchpy.client.cluster
import opensearchpy.client.indices
# from opensearchpy import AsyncOpenSearch, OpenSearch
# from opensearchpy.client.cluster import ClusterClient
# from opensearchpy.client.indices import IndicesClient


# No pytest fixtures here on purpose.
# openmock only patches during test execution, so every client must be
# instantiated inside the decorated test body.


def _index_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

@openmock
def _make_sync_client() -> opensearchpy.OpenSearch:
    return opensearchpy.OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )

@openmock
def _make_async_client() -> opensearchpy.AsyncOpenSearch:
    return opensearchpy.AsyncOpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,

    )


@openmock
def test_cluster_health_and_root_info() -> None:
    client = _make_sync_client()
    cluster =opensearchpy.client.cluster.ClusterClient(client)

    info = client.info()
    assert isinstance(info, dict)
    assert info

    health = cluster.health()
    assert isinstance(health, dict)
    assert "status" in health
    assert health["status"] in {"green", "yellow", "red"}


@openmock
def test_indices_client_lifecycle_and_metadata() -> None:
    client = _make_sync_client()
    indices =opensearchpy.client.indices.IndicesClient(client)
    index_name = _index_name("books-indices")
    alias_name = f"{index_name}-alias"

    create_resp = indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "author": {"type": "keyword"},
                    "published_year": {"type": "integer"},
                    "tags": {"type": "keyword"},
                }
            },
        },
    )
    assert create_resp.get("acknowledged") is True
    assert indices.exists(index=index_name)

    put_mapping_resp = indices.put_mapping(
        index=index_name,
        body={
            "properties": {
                "series": {"type": "keyword"},
                "pages": {"type": "integer"},
            }
        },
    )
    assert put_mapping_resp.get("acknowledged") is True

    mapping_resp = indices.get_mapping(index=index_name)
    properties = mapping_resp[index_name]["mappings"]["properties"]
    assert "title" in properties
    assert "series" in properties
    assert properties["pages"]["type"] == "integer"

    settings_resp = indices.get_settings(index=index_name)
    assert index_name in settings_resp
    assert "settings" in settings_resp[index_name]

    alias_resp = indices.put_alias(index=index_name, name=alias_name)
    assert alias_resp.get("acknowledged") is True

    get_alias_resp = indices.get_alias(index=index_name)
    assert alias_name in get_alias_resp[index_name]["aliases"]

    refresh_resp = indices.refresh(index=index_name)
    assert isinstance(refresh_resp, dict)

    stats_resp = indices.stats(index=index_name)
    assert isinstance(stats_resp, dict)
    assert "indices" in stats_resp or "_all" in stats_resp

    delete_resp = indices.delete(index=index_name)
    assert delete_resp.get("acknowledged") is True
    assert not indices.exists(index=index_name)


@openmock
def test_opensearch_document_crud_bulk_search_count_and_delete() -> None:
    client = _make_sync_client()
    indices = opensearchpy.client.indices.IndicesClient(client)
    index_name = _index_name("books-sync")

    indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "author": {"type": "keyword"},
                    "summary": {"type": "text"},
                    "published_year": {"type": "integer"},
                    "series": {"type": "keyword"},
                }
            },
        },
    )

    journey_doc = {
        "title": "Journey to the Center of the Earth",
        "author": "Jules Verne",
        "summary": "Professor Lidenbrock leads an expedition beneath Iceland.",
        "published_year": 1864,
        "series": "Extraordinary Voyages",
    }
    twenty_doc = {
        "title": "Twenty Thousand Leagues Under the Seas",
        "author": "Jules Verne",
        "summary": "Captain Nemo roams the oceans aboard the Nautilus.",
        "published_year": 1870,
        "series": "Extraordinary Voyages",
    }

    index_resp = client.index(index=index_name, id="journey", body=journey_doc, refresh=True)
    assert index_resp["result"] in {"created", "updated"}

    assert client.exists(index=index_name, id="journey") is True

    get_resp = client.get(index=index_name, id="journey")
    assert get_resp["found"] is True
    assert get_resp["_source"]["title"] == "Journey to the Center of the Earth"

    update_resp = client.update(
        index=index_name,
        id="journey",
        body={"doc": {"pages": 183}},
        refresh=True,
    )
    assert update_resp["result"] in {"updated", "noop"}

    mget_resp = client.mget(
        body={
            "docs": [
                {"_index": index_name, "_id": "journey"},
                {"_index": index_name, "_id": "missing"},
            ]
        }
    )
    assert len(mget_resp["docs"]) == 2
    assert mget_resp["docs"][0]["found"] is True
    assert mget_resp["docs"][1]["found"] is False

    bulk_resp = client.bulk(
        body=[
            {"index": {"_index": index_name, "_id": "twenty-thousand"}},
            twenty_doc,
            {"create": {"_index": index_name, "_id": "mysterious-island"}},
            {
                "title": "The Mysterious Island",
                "author": "Jules Verne",
                "summary": "Castaways build a new life and uncover a hidden benefactor.",
                "published_year": 1874,
                "series": "Extraordinary Voyages",
            },
        ],
        refresh=True,
    )
    assert bulk_resp.get("errors") is False
    assert len(bulk_resp["items"]) == 2

    search_resp = client.search(
        index=index_name,
        body={
            "size": 10,
            "query": {
                "multi_match": {
                    "query": "Nemo Nautilus",
                    "fields": ["title^2", "summary"],
                }
            },
            "sort": [{"published_year": {"order": "asc"}}],
        },
    )
    hits = search_resp["hits"]["hits"]
    assert len(hits) >= 1
    assert hits[0]["_source"]["title"] == "Twenty Thousand Leagues Under the Seas"

    count_resp = client.count(index=index_name, body={"query": {"term": {"author": "Jules Verne"}}})
    assert count_resp["count"] >= 3

    delete_resp = client.delete(index=index_name, id="journey", refresh=True)
    assert delete_resp["result"] in {"deleted", "not_found"}

    final_count_resp = client.count(index=index_name, body={"query": {"match_all": {}}})
    assert final_count_resp["count"] >= 1

    indices.delete(index=index_name)



@pytest.mark.asyncio
@openmock
async def test_async_opensearch_crud_search_and_bulk() -> None:
    client = _make_async_client()
    index_name = _index_name("books-async")

    create_resp = await client.indices.create(
        index=index_name,
        body={
            "settings": {
                "index": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                }
            },
            "mappings": {
                "properties": {
                    "title": {"type": "text"},
                    "author": {"type": "keyword"},
                    "summary": {"type": "text"},
                    "published_year": {"type": "integer"},
                }
            },
        },
    )
    assert create_resp.get("acknowledged") is True

    await client.index(
        index=index_name,
        id="journey",
        body={
            "title": "Journey to the Center of the Earth",
            "author": "Jules Verne",
            "summary": "An expedition descends into a volcanic passage.",
            "published_year": 1864,
        },
        refresh=True,
    )

    bulk_resp = await client.bulk(
        body=[
            {"index": {"_index": index_name, "_id": "around-world"}},
            {
                "title": "Around the World in Eighty Days",
                "author": "Jules Verne",
                "summary": "Phileas Fogg attempts a global journey against the clock.",
                "published_year": 1872,
            },
            {"index": {"_index": index_name, "_id": "moon"}},
            {
                "title": "From the Earth to the Moon",
                "author": "Jules Verne",
                "summary": "A post-Civil War gun club launches a projectile toward the Moon.",
                "published_year": 1865,
            },
        ],
        refresh=True,
    )
    assert bulk_resp.get("errors") is False

    exists_resp = await client.exists(index=index_name, id="journey")
    assert exists_resp is True

    get_resp = await client.get(index=index_name, id="journey")
    assert get_resp["found"] is True
    assert get_resp["_source"]["author"] == "Jules Verne"

    search_resp = await client.search(
        index=index_name,
        body={
            "query": {"match": {"summary": "journey"}},
            "sort": [{"published_year": {"order": "asc"}}],
        },
    )
    titles = [hit["_source"]["title"] for hit in search_resp["hits"]["hits"]]
    assert (
        "Journey to the Center of the Earth" in titles
        or "Around the World in Eighty Days" in titles
    )

    count_resp = await client.count(index=index_name, body={"query": {"term": {"author": "Jules Verne"}}})
    assert count_resp["count"] >= 3

    delete_resp = await client.delete(index=index_name, id="moon", refresh=True)
    assert delete_resp["result"] in {"deleted", "not_found"}

    delete_index_resp = await client.indices.delete(index=index_name)
    assert delete_index_resp.get("acknowledged") is True
