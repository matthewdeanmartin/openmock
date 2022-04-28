# -*- coding: utf-8 -*-

import unittest
from datetime import datetime

import opensearchpy

from openmock import openmock

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
        self.es = opensearchpy.OpenSearch(hosts=[{"host": "localhost", "port": 9200}])
