"""Tests for alias resolution in data operations and delete_by_query."""

import pytest

from openmock import FakeOpenSearch


@pytest.fixture
def client():
    c = FakeOpenSearch()
    c.indices.create(index="real-index")
    c.indices.put_alias(index="real-index", name="my-alias")
    return c


def test_search_via_alias(client):
    client.index(index="real-index", body={"field": "value"}, id="1")
    result = client.search(index="my-alias")
    assert result["hits"]["total"]["value"] == 1


def test_count_via_alias(client):
    client.index(index="real-index", body={"field": "value"}, id="1")
    result = client.count(index="my-alias")
    assert result["count"] == 1


def test_index_via_alias_and_search_on_real(client):
    client.index(index="real-index", body={"x": 1}, id="doc1")
    results = client.search(index="my-alias", body={"query": {"match_all": {}}})
    assert results["hits"]["total"]["value"] == 1


def test_delete_by_query(client):
    client.index(index="real-index", body={"tag": "remove-me"}, id="a")
    client.index(index="real-index", body={"tag": "keep-me"}, id="b")
    result = client.delete_by_query(
        index="real-index",
        body={"query": {"term": {"tag": "remove-me"}}},
    )
    assert result["deleted"] == 1
    remaining = client.search(index="real-index")
    assert remaining["hits"]["total"]["value"] == 1
    assert remaining["hits"]["hits"][0]["_source"]["tag"] == "keep-me"


def test_delete_by_query_via_alias(client):
    client.index(index="real-index", body={"tag": "gone"}, id="x")
    result = client.delete_by_query(
        index="my-alias",
        body={"query": {"term": {"tag": "gone"}}},
    )
    assert result["deleted"] == 1
    remaining = client.search(index="real-index")
    assert remaining["hits"]["total"]["value"] == 0


def test_search_track_total_hits_param(client):
    client.index(index="real-index", body={"v": 1}, id="1")
    result = client.search(index="real-index", params={"track_total_hits": True})
    assert result["hits"]["total"]["value"] == 1


def test_alias_swap_redirects_search(client):
    client.indices.create(index="real-index-v2")
    client.index(index="real-index", body={"v": 1}, id="old")
    client.index(index="real-index-v2", body={"v": 2}, id="new")

    client.indices.update_aliases(
        body={
            "actions": [
                {"remove": {"index": "real-index", "alias": "my-alias"}},
                {"add": {"index": "real-index-v2", "alias": "my-alias"}},
            ]
        }
    )

    result = client.search(index="my-alias")
    assert result["hits"]["total"]["value"] == 1
    assert result["hits"]["hits"][0]["_source"]["v"] == 2
