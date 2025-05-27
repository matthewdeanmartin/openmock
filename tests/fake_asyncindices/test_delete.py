from tests import INDEX_NAME, Testasyncopenmock


class TestDelete(Testasyncopenmock):
    async def test_should_delete_index(self):
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))

        await self.es.indices.create(INDEX_NAME)
        self.assertTrue(await self.es.indices.exists(INDEX_NAME))

        await self.es.indices.delete(INDEX_NAME)
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))

    async def test_should_delete_inexistent_index(self):
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))

        await self.es.indices.delete(INDEX_NAME)
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))
