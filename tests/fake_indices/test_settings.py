from openmock import FakeOpenSearch


def test_settings():
    client = FakeOpenSearch()
    index_name = "test-index"
    client.indices.create(index=index_name)

    settings = {"index": {"number_of_shards": 3, "number_of_replicas": 2}}
    client.indices.put_settings(index=index_name, body=settings)

    response = client.indices.get_settings(index=index_name)
    assert response[index_name]["settings"]["index"]["number_of_shards"] == "3"
    assert response[index_name]["settings"]["index"]["number_of_replicas"] == "2"


def test_get_settings_all():
    client = FakeOpenSearch()
    client.indices.create(index="idx1", body={"settings": {}})
    client.indices.create(index="idx2", body={"settings": {}})

    response = client.indices.get_settings()
    assert "idx1" in response
    assert "idx2" in response


def test_put_settings_flat():
    client = FakeOpenSearch()
    index_name = "flat-settings"
    client.indices.create(index=index_name)

    settings = {"number_of_shards": 5}
    client.indices.put_settings(index=index_name, body=settings)

    response = client.indices.get_settings(index=index_name)
    assert response[index_name]["settings"]["index"]["number_of_shards"] == "5"
