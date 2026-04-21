"""Tests for exists_alias, update_aliases, and enhanced get_alias."""

import pytest

from openmock import FakeOpenSearch


@pytest.fixture
def client():
    c = FakeOpenSearch()
    c.indices.create(index="index-v1")
    c.indices.create(index="index-v2")
    c.indices.put_alias(index="index-v1", name="my-alias")
    return c


def test_exists_alias_true(client):
    assert client.indices.exists_alias(name="my-alias") is True


def test_exists_alias_false(client):
    assert client.indices.exists_alias(name="no-such-alias") is False


def test_exists_alias_with_index(client):
    assert client.indices.exists_alias(index="index-v1", name="my-alias") is True
    assert client.indices.exists_alias(index="index-v2", name="my-alias") is False


def test_update_aliases_add(client):
    client.indices.update_aliases(
        body={"actions": [{"add": {"index": "index-v2", "alias": "my-alias"}}]}
    )
    aliases = client.indices.get_alias(name="my-alias")
    assert "index-v2" in aliases
    assert "my-alias" in aliases["index-v2"]["aliases"]


def test_update_aliases_remove(client):
    client.indices.update_aliases(
        body={"actions": [{"remove": {"index": "index-v1", "alias": "my-alias"}}]}
    )
    assert not client.indices.exists_alias(name="my-alias")


def test_update_aliases_atomic_swap(client):
    client.indices.update_aliases(
        body={
            "actions": [
                {"remove": {"index": "index-v1", "alias": "my-alias"}},
                {"add": {"index": "index-v2", "alias": "my-alias"}},
            ]
        }
    )
    aliases = client.indices.get_alias(name="my-alias")
    assert "index-v2" in aliases
    assert "index-v1" not in aliases


def test_get_alias_by_name_filters(client):
    client.indices.put_alias(index="index-v1", name="other-alias")
    result = client.indices.get_alias(name="my-alias")
    assert "index-v1" in result
    assert "my-alias" in result["index-v1"]["aliases"]
    assert "other-alias" not in result["index-v1"]["aliases"]


def test_get_alias_no_index_no_name_returns_all(client):
    result = client.indices.get_alias()
    assert "index-v1" in result
    assert "my-alias" in result["index-v1"]["aliases"]
