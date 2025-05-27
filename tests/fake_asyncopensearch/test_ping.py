from tests import Testasyncopenmock


class TestPing(Testasyncopenmock):
    async def test_should_return_true_when_ping(self):
        self.assertTrue(await self.es.ping())
