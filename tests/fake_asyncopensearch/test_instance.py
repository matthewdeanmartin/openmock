import opensearchpy

from openmock import openmock, AsyncFakeOpenSearch
from tests import Testasyncopenmock


class TestInstance(Testasyncopenmock):
    async def test_should_create_fake_opensearchpy_instance(self):
        self.assertIsInstance(self.es, AsyncFakeOpenSearch)

    @openmock
    async def test_should_return_same_open_instance_when_instantiate_more_than_one_instance_with_same_host(
        self,
    ):
        es1 = opensearchpy.AsyncOpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        es2 = opensearchpy.AsyncOpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        self.assertEqual(es1, es2)
