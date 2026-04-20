import asyncio
import unittest
from datetime import datetime

import aiounittest
import opensearchpy

from tests.backend import (
    close_test_client_async,
    close_test_client_sync,
    get_test_hosts,
    openmock,
    using_real_opensearch,
)

INDEX_NAME = "test_index"
DOC_TYPE = "doc-Type"
DOC_ID = "doc-id"
BODY = {
    "author": "kimchy",
    "text": "opensearchpy: cool. bonsai cool.",
    "timestamp": datetime.now(),
}


class Testopenmock(unittest.TestCase):
    @openmock
    def setUp(self):
        self.es = opensearchpy.OpenSearch(hosts=get_test_hosts())

    def tearDown(self):
        if using_real_opensearch() and getattr(self, "es", None) is not None:
            close_test_client_sync(self.es)


class Testasyncopenmock(aiounittest.AsyncTestCase):
    @openmock
    def setUp(self):
        self.es = opensearchpy.AsyncOpenSearch(hosts=get_test_hosts())

    def tearDown(self):
        if using_real_opensearch() and getattr(self, "es", None) is not None:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(close_test_client_async(self.es))
                loop.close()
            except Exception:
                pass
