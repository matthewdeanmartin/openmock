import pytest
from opensearchpy.exceptions import RequestError
from openmock import FakeOpenSearch


def test_create_invalid_name():
    client = FakeOpenSearch()
    with pytest.raises(RequestError) as excinfo:
        client.indices.create(index="invalid name")
    assert "invalid_index_name_exception" in str(excinfo.value)

    with pytest.raises(RequestError):
        client.indices.create(index="invalid*name")
