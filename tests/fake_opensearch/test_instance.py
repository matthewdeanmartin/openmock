# -*- coding: utf-8 -*-

import opensearchpy

from openmock import openmock
from openmock.fake_opensearch import FakeOpenSearch
from tests import Testopenmock


class TestInstance(Testopenmock):

    def test_should_create_fake_opensearchpy_instance(self):
        self.assertIsInstance(self.es, FakeOpenSearch)

    @openmock
    def test_should_return_same_open_instance_when_instantiate_more_than_one_instance_with_same_host(self):
        es1 = opensearchpy.OpenSearch(hosts=[{'host': 'localhost', 'port': 9200}])
        es2 = opensearchpy.OpenSearch(hosts=[{'host': 'localhost', 'port': 9200}])
        self.assertEqual(es1, es2)
