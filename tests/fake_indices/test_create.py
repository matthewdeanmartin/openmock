# -*- coding: utf-8 -*-

from tests import Testopenmock, INDEX_NAME


class TestCreate(Testopenmock):

    def test_should_create_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))
        self.es.indices.create(INDEX_NAME)
        self.assertTrue(self.es.indices.exists(INDEX_NAME))
