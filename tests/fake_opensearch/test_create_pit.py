import time
from opensearchpy.client.utils import SKIP_IN_PATH

from tests import INDEX_NAME, Testopenmock


class TestCreatePit(Testopenmock):
    def test_should_create_pit_successfully(self):
        result = self.es.create_pit(index=INDEX_NAME)

        self.assertIn("pit_id", result)
        self.assertIn("_shards", result)
        self.assertIn("creation_time", result)

        self.assertIsInstance(result["pit_id"], str)

        shards = result["_shards"]
        self.assertEqual(shards["total"], 1)
        self.assertEqual(shards["successful"], 1)
        self.assertEqual(shards["skipped"], 0)
        self.assertEqual(shards["failed"], 0)

        self.assertIsInstance(result["creation_time"], int)
        current_time = int(time.time() * 1000)
        self.assertLessEqual(abs(result["creation_time"] - current_time), 1000)

    def test_should_create_pit_with_params(self):
        params = {
            "keep_alive": "5m",
            "preference": "_local",
            "routing": "user_id",
            "allow_partial_pit_creation": True,
        }

        result = self.es.create_pit(index=INDEX_NAME, params=params)
        self.assertIn("pit_id", result)
        self.assertIn("_shards", result)
        self.assertIn("creation_time", result)

    def test_should_create_pit_with_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
        }

        result = self.es.create_pit(index=INDEX_NAME, headers=headers)
        self.assertIn("pit_id", result)
        self.assertIn("_shards", result)
        self.assertIn("creation_time", result)

    def test_should_raise_valueerror_for_empty_index(self):
        for empty_index in SKIP_IN_PATH:
            with self.assertRaises(ValueError) as context:
                self.es.create_pit(index=empty_index)
            self.assertIn(
                "Empty value passed for a required argument 'index'",
                str(context.exception),
            )

    def test_should_work_with_different_index_names(self):
        index_names = [
            "test-index",
            "test_index",
            "test.index",
            "TestIndex",
            "index123",
            "my-app-logs-2023",
        ]

        for index_name in index_names:
            result = self.es.create_pit(index=index_name)
            self.assertIn("pit_id", result)
            self.assertIn("_shards", result)
            self.assertIn("creation_time", result)
            self.assertEqual(len(result["pit_id"]), 168)
