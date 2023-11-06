from tests import Testopenmock


class TestInfo(Testopenmock):
    def test_should_return_status_200_for_info(self):
        info = self.es.info()
        self.assertEqual(info.get("status"), 200)
