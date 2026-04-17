import opensearchpy

from openmock import AsyncFakeOpenSearch
from tests import Testasyncopenmock
from tests.backend import mock_only, openmock


class TestInstance(Testasyncopenmock):
    @mock_only("This assertion is specific to the in-memory fake client.")
    async def test_should_create_fake_opensearchpy_instance(self):
        self.assertIsInstance(self.es, AsyncFakeOpenSearch)

    @mock_only("Instance caching is a mock implementation detail, not parity behavior.")
    @openmock
    async def test_should_return_same_open_instance_when_instantiate_more_than_one_instance_with_same_host(
        self,
    ):
        es1 = opensearchpy.AsyncOpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        es2 = opensearchpy.AsyncOpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        self.assertEqual(es1, es2)
