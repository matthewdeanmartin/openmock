from unittest import TestCase

import opensearchpy

from tests.backend import openmock


class TestAggregations(TestCase):
    @openmock
    def test_terms_aggregation(self):
        es = opensearchpy.OpenSearch()
        es.index(index="test-index", body={"category": "A"})
        es.index(index="test-index", body={"category": "A"})
        es.index(index="test-index", body={"category": "B"})

        query = {"aggs": {"categories": {"terms": {"field": "category"}}}}

        res = es.search(index="test-index", body=query)

        self.assertIn("aggregations", res)
        self.assertIn("categories", res["aggregations"])
        buckets = res["aggregations"]["categories"]["buckets"]
        self.assertEqual(len(buckets), 2)

        # Sort buckets by key for stable assertion if needed,
        # but my implementation sorts by doc_count
        self.assertEqual(buckets[0]["key"], "A")
        self.assertEqual(buckets[0]["doc_count"], 2)
        self.assertEqual(buckets[1]["key"], "B")
        self.assertEqual(buckets[1]["doc_count"], 1)
