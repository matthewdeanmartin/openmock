from tests import Testasyncopenmock


class TestInfo(Testasyncopenmock):
    async def test_should_return_info_payload(self):
        info = await self.es.info()
        self.assertIn("cluster_name", info)
        self.assertIn("version", info)
        self.assertIn("number", info["version"])
        self.assertNotIn("status", info)
