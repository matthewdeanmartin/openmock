from tests import INDEX_NAME, Testasyncopenmock


class TestExists(Testasyncopenmock):
    async def test_should_return_false_when_index_does_not_exists(self):
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))

    async def test_should_return_true_when_index_exists(self):
        await self.es.indices.create(INDEX_NAME)
        self.assertTrue(await self.es.indices.exists(INDEX_NAME))
