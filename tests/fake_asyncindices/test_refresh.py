from tests import INDEX_NAME, Testasyncopenmock


class TestRefresh(Testasyncopenmock):
    async def test_should_refresh_index(self):
        await self.es.indices.create(INDEX_NAME)
        await self.es.indices.refresh(INDEX_NAME)
        self.assertTrue(await self.es.indices.exists(INDEX_NAME))
