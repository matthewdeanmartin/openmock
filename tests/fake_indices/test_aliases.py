from openmock import FakeOpenSearch


def test_aliases():
    client = FakeOpenSearch()
    client.indices.create(index="test-index")

    client.indices.put_alias(index="test-index", name="test-alias")

    aliases = client.indices.get_alias(index="test-index")
    assert "test-alias" in aliases["test-index"]["aliases"]

    aliases = client.indices.get_alias(name="test-alias")
    assert "test-index" in aliases
    assert "test-alias" in aliases["test-index"]["aliases"]

    client.indices.delete_alias(index="test-index", name="test-alias")
    aliases = client.indices.get_alias(index="test-index")
    assert "test-alias" not in aliases["test-index"]["aliases"]


def test_aliases_multiple_indices():
    client = FakeOpenSearch()
    client.indices.create(index="index1")
    client.indices.create(index="index2")

    client.indices.put_alias(index="index1,index2", name="multi-alias")

    aliases = client.indices.get_alias(index="index1")
    assert "multi-alias" in aliases["index1"]["aliases"]

    aliases = client.indices.get_alias(index="index2")
    assert "multi-alias" in aliases["index2"]["aliases"]
