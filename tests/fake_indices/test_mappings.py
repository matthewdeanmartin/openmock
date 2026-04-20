from openmock import FakeOpenSearch


def test_mappings():
    client = FakeOpenSearch()
    index_name = "test-index"
    client.indices.create(index=index_name)

    mapping = {"properties": {"title": {"type": "text"}, "content": {"type": "text"}}}
    client.indices.put_mapping(index=index_name, body=mapping)

    response = client.indices.get_mapping(index=index_name)
    assert response[index_name]["mappings"]["properties"]["title"]["type"] == "text"
    assert response[index_name]["mappings"]["properties"]["content"]["type"] == "text"


def test_put_mapping_on_missing_index():
    client = FakeOpenSearch()
    index_name = "missing-index"

    mapping = {"properties": {"f": {"type": "keyword"}}}
    client.indices.put_mapping(index=index_name, body=mapping)

    response = client.indices.get_mapping(index=index_name)
    assert response[index_name]["mappings"]["properties"]["f"]["type"] == "keyword"


def test_get_mapping_all():
    client = FakeOpenSearch()
    client.indices.create(index="idx1", body={"mappings": {}})
    client.indices.create(index="idx2", body={"mappings": {}})

    response = client.indices.get_mapping()
    assert "idx1" in response
    assert "idx2" in response
