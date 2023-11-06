from tests import INDEX_NAME, Testopenmock


class TestDelete(Testopenmock):
    def test_should_delete_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

        self.es.indices.create(INDEX_NAME)
        self.assertTrue(self.es.indices.exists(INDEX_NAME))

        self.es.indices.delete(INDEX_NAME)
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

    def test_should_delete_inexistent_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))

        self.es.indices.delete(INDEX_NAME)
        self.assertFalse(self.es.indices.exists(INDEX_NAME))
