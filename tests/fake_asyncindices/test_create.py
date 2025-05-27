from tests import INDEX_NAME, Testasyncopenmock


class TestCreate(Testasyncopenmock):
    async def test_should_create_index(self):
        self.assertFalse(await self.es.indices.exists(INDEX_NAME))
        await self.es.indices.create(INDEX_NAME)
        self.assertTrue(await self.es.indices.exists(INDEX_NAME))
