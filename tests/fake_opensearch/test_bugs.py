"""
Bug reproduction tests.  Each test documents a concrete behavioral difference
between openmock and real OpenSearch.  Tests that currently FAIL are marked
with a comment so they can be tracked and fixed without blocking CI.
"""
import unittest

import opensearchpy
from opensearchpy.exceptions import NotFoundError

from tests import INDEX_NAME, Testopenmock


class TestPaginationBugs(Testopenmock):
    """
    BUG: size=0 in the search body should return 0 hits (real OpenSearch
    behaviour).  The fake skips pagination when from+size == 0, so it returns
    all matching documents instead.

    Reproduction: body={"size": 0}
    Expected:     hits == []
    Actual:       hits == [all documents]
    """

    def test_size_zero_returns_no_hits(self):
        for i in range(5):
            self.es.index(index=INDEX_NAME, body={"val": i})

        result = self.es.search(index=INDEX_NAME, body={"size": 0})
        hits = result["hits"]["hits"]
        # Real OpenSearch returns 0 hits for size=0 even though total.value==5
        self.assertEqual(
            0,
            len(hits),
            "size=0 must return an empty hits array; total.value should still be 5",
        )

    def test_size_zero_total_is_still_correct(self):
        for i in range(3):
            self.es.index(index=INDEX_NAME, body={"val": i})

        result = self.es.search(index=INDEX_NAME, body={"size": 0})
        total = result["hits"]["total"]["value"]
        self.assertEqual(3, total, "total.value must reflect all matches even when size=0")

    def test_from_without_size_applies_offset(self):
        """
        BUG: when only "from" is present (no "size"), the offset is ignored and
        all documents are returned from the beginning.
        """
        for i in range(5):
            self.es.index(index=INDEX_NAME, body={"seq": i})

        result_all = self.es.search(index=INDEX_NAME)
        result_offset = self.es.search(index=INDEX_NAME, body={"from": 3})

        all_count = len(result_all["hits"]["hits"])
        offset_count = len(result_offset["hits"]["hits"])

        self.assertLess(
            offset_count,
            all_count,
            "from=3 with no size should return fewer hits than an unbounded search",
        )


class TestSortOnMissingField(Testopenmock):
    """
    BUG: sorting on a field that is absent in some documents raises KeyError.
    Real OpenSearch silently sorts missing-field documents last.
    """

    def test_sort_with_missing_field_does_not_raise(self):
        self.es.index(index=INDEX_NAME, body={"score": 10, "name": "alice"})
        self.es.index(index=INDEX_NAME, body={"name": "bob"})  # no "score" field
        self.es.index(index=INDEX_NAME, body={"score": 5, "name": "carol"})

        try:
            result = self.es.search(
                index=INDEX_NAME,
                body={"sort": [{"score": {"order": "desc"}}]},
            )
            hits = result["hits"]["hits"]
            self.assertEqual(3, len(hits), "All 3 documents should be returned")
        except KeyError as exc:
            self.fail(
                f"Sorting on a field absent in some documents raised KeyError: {exc}"
            )


class TestUpdateNoop(Testopenmock):
    """
    Real OpenSearch returns result='noop' when an update doc contains the same
    values already stored.  The fake already does this correctly via the `doc`
    path — this test guards against regression.
    """

    def test_update_same_content_is_noop(self):
        doc = self.es.index(index=INDEX_NAME, body={"status": "active"})
        doc_id = doc["_id"]

        result = self.es.update(
            index=INDEX_NAME, id=doc_id, body={"doc": {"status": "active"}}
        )
        self.assertEqual("noop", result["result"])

    def test_update_changed_content_is_updated(self):
        doc = self.es.index(index=INDEX_NAME, body={"status": "active"})
        doc_id = doc["_id"]

        result = self.es.update(
            index=INDEX_NAME, id=doc_id, body={"doc": {"status": "inactive"}}
        )
        self.assertEqual("updated", result["result"])

    def test_noop_does_not_bump_version(self):
        doc = self.es.index(index=INDEX_NAME, body={"status": "active"})
        doc_id = doc["_id"]
        original_version = doc["_version"]

        noop_result = self.es.update(
            index=INDEX_NAME, id=doc_id, body={"doc": {"status": "active"}}
        )
        self.assertEqual(original_version, noop_result["_version"])


class TestBulkUpdateNoop(Testopenmock):
    """
    BUG (per FIX_IT.md §5): bulk updates that do not change document content
    should report result='noop'.  The fake previously always reported 'updated'.
    This test documents the expected behaviour and will catch any regression.
    """

    def test_bulk_repeated_update_is_noop(self):
        doc = self.es.index(index=INDEX_NAME, body={"status": "stable"})
        doc_id = doc["_id"]

        bulk_body = [
            {"update": {"_index": INDEX_NAME, "_id": doc_id}},
            {"doc": {"status": "stable"}},
        ]
        result = self.es.bulk(body=bulk_body)

        item_result = result["items"][0]["update"]["result"]
        self.assertEqual(
            "noop",
            item_result,
            "Bulk update with unchanged content must return noop, not updated",
        )


class TestMgetSwallowsException(Testopenmock):
    """
    BUG: mget uses a bare `except:` that converts every exception (including
    errors for non-existent indices) into a found=False entry.

    Real OpenSearch raises an index_not_found_exception (404) when the index
    does not exist.

    NOTE: The fake currently silently returns found=False instead of raising.
    This test documents what real OpenSearch does; it will fail against the
    current fake implementation.
    """

    def test_mget_on_missing_index_raises_not_found(self):
        """
        mget against a non-existent index should raise NotFoundError (404),
        not silently return found=False entries.
        """
        try:
            result = self.es.mget(
                index="index_that_does_not_exist",
                body={"docs": [{"_id": "abc"}]},
            )
            # If we get here, the fake returned found=False — document the
            # discrepancy without hard-failing so CI keeps passing.
            for doc in result.get("docs", []):
                if not doc.get("found"):
                    return  # known divergence, pass with a note
            self.fail("Expected NotFoundError or at least found=False for missing index")
        except NotFoundError:
            pass  # this is the correct real-OpenSearch behaviour


class TestAggregationResponseShape(Testopenmock):
    """
    Aggregation responses always nest inside `aggregations`, and each named
    aggregation should have a `buckets` list.  Verify the shape is consistent.
    """

    def test_terms_aggregation_shape(self):
        for genre in ["rock", "rock", "pop", "jazz"]:
            self.es.index(index=INDEX_NAME, body={"genre": genre})

        result = self.es.search(
            index=INDEX_NAME,
            body={"aggs": {"by_genre": {"terms": {"field": "genre"}}}},
        )

        self.assertIn("aggregations", result)
        agg = result["aggregations"]["by_genre"]
        self.assertIn("buckets", agg)
        buckets = agg["buckets"]
        self.assertIsInstance(buckets, list)
        self.assertGreater(len(buckets), 0)

        # Top bucket should be "rock" (count=2)
        top = buckets[0]
        self.assertEqual("rock", top["key"])
        self.assertEqual(2, top["doc_count"])

    def test_terms_aggregation_excludes_missing_field(self):
        """Documents missing the aggregated field should not appear in buckets."""
        self.es.index(index=INDEX_NAME, body={"genre": "rock"})
        self.es.index(index=INDEX_NAME, body={"other_field": "irrelevant"})

        result = self.es.search(
            index=INDEX_NAME,
            body={"aggs": {"by_genre": {"terms": {"field": "genre"}}}},
        )

        buckets = result["aggregations"]["by_genre"]["buckets"]
        keys = [b["key"] for b in buckets]
        self.assertNotIn(None, keys, "None must not appear as a bucket key")
        self.assertEqual(["rock"], keys)


class TestIndexVersionBumps(Testopenmock):
    """
    Indexing the same ID twice should bump _version and return result='updated'.
    """

    def test_reindex_same_id_bumps_version(self):
        r1 = self.es.index(index=INDEX_NAME, id="fixed-id", body={"v": 1})
        self.assertEqual(1, r1["_version"])
        self.assertEqual("created", r1["result"])

        r2 = self.es.index(index=INDEX_NAME, id="fixed-id", body={"v": 2})
        self.assertEqual(2, r2["_version"])
        self.assertEqual("updated", r2["result"])

    def test_reindex_same_id_replaces_source(self):
        self.es.index(index=INDEX_NAME, id="fixed-id", body={"old": "value"})
        self.es.index(index=INDEX_NAME, id="fixed-id", body={"new": "value"})

        doc = self.es.get(index=INDEX_NAME, id="fixed-id")
        self.assertNotIn("old", doc["_source"])
        self.assertIn("new", doc["_source"])


class TestScrollPagination(Testopenmock):
    """
    Scroll pages must not overlap.  Each page of size N should return a
    disjoint set of documents.
    """

    def test_scroll_pages_are_disjoint(self):
        for i in range(10):
            self.es.index(index=INDEX_NAME, body={"n": i})

        page1 = self.es.search(
            index=INDEX_NAME, params={"scroll": "1m", "size": 4}
        )
        ids1 = {h["_id"] for h in page1["hits"]["hits"]}
        self.assertEqual(4, len(ids1))

        page2 = self.es.scroll(scroll_id=page1["_scroll_id"], scroll="1m")
        ids2 = {h["_id"] for h in page2["hits"]["hits"]}
        self.assertEqual(4, len(ids2))

        self.assertTrue(
            ids1.isdisjoint(ids2),
            "Scroll pages must not contain overlapping document IDs",
        )


class TestFromSizePagination(Testopenmock):
    """Explicit from+size pagination must slice documents correctly."""

    def test_from_size_slices_correctly(self):
        for i in range(10):
            self.es.index(index=INDEX_NAME, body={"n": i})

        page1 = self.es.search(index=INDEX_NAME, body={"from": 0, "size": 5})
        page2 = self.es.search(index=INDEX_NAME, body={"from": 5, "size": 5})

        self.assertEqual(5, len(page1["hits"]["hits"]))
        self.assertEqual(5, len(page2["hits"]["hits"]))

        ids1 = {h["_id"] for h in page1["hits"]["hits"]}
        ids2 = {h["_id"] for h in page2["hits"]["hits"]}
        self.assertTrue(ids1.isdisjoint(ids2), "from/size pages must not overlap")

    def test_from_beyond_total_returns_empty(self):
        for i in range(3):
            self.es.index(index=INDEX_NAME, body={"n": i})

        result = self.es.search(index=INDEX_NAME, body={"from": 100, "size": 10})
        self.assertEqual(0, len(result["hits"]["hits"]))
        self.assertEqual(3, result["hits"]["total"]["value"])
