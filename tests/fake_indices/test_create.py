from tests import INDEX_NAME, Testopenmock


class TestCreate(Testopenmock):
    def test_should_create_index(self):
        self.assertFalse(self.es.indices.exists(INDEX_NAME))
        self.es.indices.create(INDEX_NAME)
        self.assertTrue(self.es.indices.exists(INDEX_NAME))
