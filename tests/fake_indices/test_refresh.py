# -*- coding: utf-8 -*-

from tests import Testopenmock, INDEX_NAME


class TestRefresh(Testopenmock):

    def test_should_refresh_index(self):
        self.es.indices.create(INDEX_NAME)
        self.es.indices.refresh(INDEX_NAME)
        self.assertTrue(self.es.indices.exists(INDEX_NAME))
