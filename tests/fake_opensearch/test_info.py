from tests import Testopenmock


class TestInfo(Testopenmock):
    def test_should_return_info_payload(self):
        info = self.es.info()
        self.assertIn("cluster_name", info)
        self.assertIn("version", info)
        self.assertIn("number", info["version"])
        self.assertNotIn("status", info)
