import opensearchpy

from openmock.fake_opensearch import FakeOpenSearch
from tests import Testopenmock
from tests.backend import mock_only, openmock


class TestInstance(Testopenmock):
    @mock_only("This assertion is specific to the in-memory fake client.")
    def test_should_create_fake_opensearchpy_instance(self):
        self.assertIsInstance(self.es, FakeOpenSearch)

    @mock_only("Instance caching is a mock implementation detail, not parity behavior.")
    @openmock
    def test_should_return_same_open_instance_when_instantiate_more_than_one_instance_with_same_host(
        self,
    ):
        es1 = opensearchpy.OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        es2 = opensearchpy.OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
        self.assertEqual(es1, es2)
