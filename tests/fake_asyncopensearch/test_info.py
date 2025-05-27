from tests import Testasyncopenmock


class TestInfo(Testasyncopenmock):
    async def test_should_return_status_200_for_info(self):
        info = await self.es.info()
        self.assertEqual(info.get("status"), 200)
