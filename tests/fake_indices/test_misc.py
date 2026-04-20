from openmock import FakeOpenSearch


def test_stats():
    client = FakeOpenSearch()
    client.indices.create(index="test-index")

    response = client.indices.stats(index="test-index")
    assert "_shards" in response
    assert "test-index" in response["indices"]


def test_analyze():
    client = FakeOpenSearch()
    response = client.indices.analyze(body={"text": "hello world"})
    assert "tokens" in response
    assert response["tokens"] == []


def test_normalize_index_to_list():
    client = FakeOpenSearch()
    # Access private method for testing normalize_index_to_list coverage
    # Actually we can just call it through public methods if they use it.
    # get_alias uses it.
    client.indices.create(index="idx1")
    client.indices.create(index="idx2")

    # Test "*"
    res = client.indices.get_alias(index="*")
    assert "idx1" in res
    assert "idx2" in res

    # Test list
    res = client.indices.get_alias(index=["idx1"])
    assert "idx1" in res
    assert "idx2" not in res
