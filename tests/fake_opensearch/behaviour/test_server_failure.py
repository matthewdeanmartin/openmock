from openmock import behaviour
from tests import BODY, DOC_TYPE, INDEX_NAME
from tests.backend import mock_only
from tests.fake_opensearch.behaviour import TestopenmockBehaviour


class TestBehaviourServerFailure(TestopenmockBehaviour):
    @mock_only("behaviour.server_failure only exists in openmock, not real OpenSearch.")
    def test_should_return_internal_server_error_when_simulate_server_error_is_true(
        self,
    ):
        behaviour.server_failure.enable()
        data = self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        expected = {"status_code": 500, "error": "Internal Server Error"}

        self.assertDictEqual(expected, data)
