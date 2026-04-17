from tests import Testopenmock


class TestHealth(Testopenmock):
    def test_should_return_health(self):
        health_status = self.es.cluster.health()
        self.assertIn("cluster_name", health_status)
        self.assertIn(health_status["status"], {"green", "yellow"})
        self.assertFalse(health_status["timed_out"])
        self.assertGreaterEqual(health_status["number_of_nodes"], 1)
        self.assertGreaterEqual(health_status["number_of_data_nodes"], 1)
        self.assertGreaterEqual(health_status["active_primary_shards"], 0)
        self.assertGreaterEqual(health_status["active_shards"], 0)
        self.assertGreaterEqual(health_status["relocating_shards"], 0)
        self.assertGreaterEqual(health_status["initializing_shards"], 0)
        self.assertGreaterEqual(health_status["unassigned_shards"], 0)
        self.assertGreaterEqual(health_status["delayed_unassigned_shards"], 0)
        self.assertGreaterEqual(health_status["number_of_pending_tasks"], 0)
        self.assertGreaterEqual(health_status["number_of_in_flight_fetch"], 0)
        self.assertGreaterEqual(health_status["task_max_waiting_in_queue_millis"], 0)
        self.assertGreaterEqual(health_status["active_shards_percent_as_number"], 0.0)
