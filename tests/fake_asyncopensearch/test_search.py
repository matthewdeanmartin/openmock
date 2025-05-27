import datetime

from opensearchpy.exceptions import NotFoundError
from parameterized import parameterized

from tests import DOC_TYPE, INDEX_NAME, Testasyncopenmock


class TestSearch(Testasyncopenmock):
    async def test_should_raise_notfounderror_when_search_for_unexistent_index(self):
        with self.assertRaises(NotFoundError):
            await self.es.search(index=INDEX_NAME)

    async def test_should_return_hits_hits_even_when_no_result(self):
        search = await self.es.search()
        self.assertEqual(0, search.get("hits").get("total").get("value"))
        self.assertListEqual([], search.get("hits").get("hits"))

    async def test_should_return_skipped_shards(self):
        search = await self.es.search()
        self.assertEqual(0, search.get("_shards").get("skipped"))

    async def test_should_return_all_documents(self):
        index_quantity = 10
        for i in range(0, index_quantity):
            await self.es.index(
                index=f"index_{i}",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        search = await self.es.search()
        self.assertEqual(index_quantity, search.get("hits").get("total").get("value"))

    async def test_should_return_all_documents_match_all(self):
        index_quantity = 10
        for i in range(0, index_quantity):
            await self.es.index(
                index=f"index_{i}",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        search = await self.es.search(body={"query": {"match_all": {}}})
        self.assertEqual(index_quantity, search.get("hits").get("total").get("value"))

    async def test_should_return_only_indexed_documents_on_index(self):
        index_quantity = 2
        for i in range(0, index_quantity):
            await self.es.index(
                index=INDEX_NAME, doc_type=DOC_TYPE, body={"data": f"test_{i}"}
            )

        search = await self.es.search(index=INDEX_NAME)
        self.assertEqual(index_quantity, search.get("hits").get("total").get("value"))

    # https://github.com/elastic/elasticsearch-py/issues/846
    # def test_should_return_only_indexed_documents_on_index_with_doc_type(self):
    #     index_quantity = 2
    #     for i in range(0, index_quantity):
    #         await self.es.index(
    #             index=INDEX_NAME, doc_type=DOC_TYPE, body={"data": f"test_{i}"}
    #         )
    #     await self.es.index(
    #         index=INDEX_NAME, doc_type="another-Doctype", body={"data": "test"}
    #     )
    #
    #     search = await self.es.search(index=INDEX_NAME, doc_type=DOC_TYPE)
    #     self.assertEqual(index_quantity, search.get("hits").get("total").get("value"))

    async def test_should_search_in_multiple_indexes(self):
        await self.es.index(index="groups", doc_type="groups", body={"budget": 1000})
        await self.es.index(index="users", doc_type="users", body={"name": "toto"})
        await self.es.index(index="pcs", doc_type="pcs", body={"model": "macbook"})

        result = await self.es.search(index=["users", "pcs"])
        self.assertEqual(2, result.get("hits").get("total").get("value"))

    async def test_usage_of_aggregations(self):
        await self.es.index(index="index", doc_type="document", body={"genre": "rock"})

        body = {"aggs": {"genres": {"terms": {"field": "genre"}}}}
        result = await self.es.search(index="index", body=body)

        self.assertTrue("aggregations" in result)

    async def test_search_with_scroll_param(self):
        for _ in range(100):
            await self.es.index(
                index="groups", doc_type="groups", body={"budget": 1000}
            )

        result = await self.es.search(
            index="groups", params={"scroll": "1m", "size": 30}
        )
        self.assertNotEqual(None, result.get("_scroll_id", None))
        self.assertEqual(30, len(result.get("hits").get("hits")))
        self.assertEqual(100, result.get("hits").get("total").get("value"))

    async def test_search_with_match_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data": "TEST"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 10)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 10)

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data": "3"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_source"], {"data": "test_3"})

    async def test_search_with_match_keyword_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": "test_{0}".format(i)},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data.keyword": "TEST"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 0)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 0)

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data.keyword": "TEST_1"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_source"], {"data": "test_1"})

    async def test_search_with_match_query_in_int_list(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search", doc_type=DOC_TYPE, body={"data": [i, 11, 13]}
            )
        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data": 1}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_source"], {"data": [1, 11, 13]})

    async def test_search_with_match_query_in_string_list(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": [str(i), "two", "three"]},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"match": {"data": "1"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_source"], {"data": ["1", "two", "three"]})

    async def test_search_with_term_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"term": {"data": "TEST"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 0)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 0)

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"term": {"data": "3"}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["_source"], {"data": "test_3"})

    async def test_search_with_bool_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search", doc_type=DOC_TYPE, body={"id": i}
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"bool": {"filter": [{"term": {"id": 1}}]}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 1)

    async def test_search_with_must_not_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search", doc_type=DOC_TYPE, body={"id": i}
            )
        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={
                "query": {
                    "bool": {
                        "filter": [{"terms": {"id": [1, 2]}}],
                        "must_not": [{"term": {"id": 1}}],
                    }
                }
            },
        )
        self.assertEqual(response["hits"]["total"]["value"], 1)
        doc = response["hits"]["hits"][0]["_source"]
        self.assertEqual(2, doc["id"])

    async def test_search_with_terms_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search", doc_type=DOC_TYPE, body={"id": i}
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"terms": {"id": [1, 2, 3]}}},
        )
        self.assertEqual(response["hits"]["total"]["value"], 3)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 3)

    async def test_query_on_nested_data(self):
        for i, y in enumerate(["yes", "no"]):
            await self.es.index(
                "index_for_search",
                doc_type=DOC_TYPE,
                body={"id": i, "data": {"x": i, "y": y}},
            )

        for term, value, i in [("data.x", 1, 1), ("data.y", "yes", 0)]:
            response = await self.es.search(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"query": {"term": {term: value}}},
            )
            self.assertEqual(1, response["hits"]["total"]["value"])
            doc = response["hits"]["hits"][0]["_source"]
            self.assertEqual(i, doc["id"])

    async def test_search_with_bool_query_and_multi_match(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={
                    "data": f"test_{i}" if i % 2 == 0 else None,
                    "data2": f"test_{i}" if (i + 1) % 2 == 0 else None,
                },
            )

        search_body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {"query": "test", "fields": ["data", "data2"]}
                    }
                }
            }
        }
        response = await self.es.search(
            index="index_for_search", doc_type=DOC_TYPE, body=search_body
        )
        self.assertEqual(response["hits"]["total"]["value"], 10)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 10)

    async def test_search_bool_should_match_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"data": "test_0"}},
                            {"match": {"data": "test_1"}},
                            {"match": {"data": "test_2"}},
                        ]
                    }
                }
            },
        )
        self.assertEqual(response["hits"]["total"]["value"], 3)
        hits = response["hits"]["hits"]
        self.assertEqual(len(hits), 3)
        self.assertEqual(hits[0]["_source"], {"data": "test_0"})

    async def test_msearch(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search1",
                doc_type=DOC_TYPE,
                body={
                    "data": f"test_{i}" if i % 2 == 0 else None,
                    "data2": f"test_{i}" if (i + 1) % 2 == 0 else None,
                },
            )
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search2",
                doc_type=DOC_TYPE,
                body={
                    "data": f"test_{i}" if i % 2 == 0 else None,
                    "data2": f"test_{i}" if (i + 1) % 2 == 0 else None,
                },
            )

        search_body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {"query": "test", "fields": ["data", "data2"]}
                    }
                }
            }
        }
        body = []
        body.append({"index": "index_for_search1"})
        body.append(search_body)
        body.append({"index": "index_for_search2"})
        body.append(search_body)

        result = await self.es.msearch(index="index_for_search", body=body)
        response1, response2 = result["responses"]
        self.assertEqual(response1["hits"]["total"]["value"], 10)
        hits1 = response1["hits"]["hits"]
        self.assertEqual(len(hits1), 10)
        self.assertEqual(response2["hits"]["total"]["value"], 10)
        hits2 = response2["hits"]["hits"]
        self.assertEqual(len(hits2), 10)

    @parameterized.expand(
        [
            (
                "timestamp gt",
                {
                    "timestamp": {
                        "gt": datetime.datetime(2009, 1, 1, 10, 20, 0).isoformat()
                    }
                },
                range(5, 12),
            ),
            (
                "timestamp gte",
                {
                    "timestamp": {
                        "gte": datetime.datetime(2009, 1, 1, 10, 20, 0).isoformat()
                    }
                },
                range(4, 12),
            ),
            (
                "timestamp lt",
                {
                    "timestamp": {
                        "lt": datetime.datetime(2009, 1, 1, 10, 35, 0).isoformat()
                    }
                },
                range(7),
            ),
            (
                "timestamp lte",
                {
                    "timestamp": {
                        "lte": datetime.datetime(2009, 1, 1, 10, 35, 0).isoformat()
                    }
                },
                range(8),
            ),
            (
                "timestamp combination",
                {
                    "timestamp": {
                        "gt": datetime.datetime(2009, 1, 1, 10, 15, 0).isoformat(),
                        "lte": datetime.datetime(2009, 1, 1, 10, 35, 0).isoformat(),
                    }
                },
                range(4, 8),
            ),
            (
                "data_int gt",
                {"data_int": {"gt": 40}},
                range(5, 12),
            ),
            (
                "data_int gte",
                {"data_int": {"gte": 40}},
                range(4, 12),
            ),
            (
                "data_int lt",
                {"data_int": {"lt": 70}},
                range(7),
            ),
            (
                "data_int lte",
                {"data_int": {"lte": 70}},
                range(8),
            ),
            (
                "data_int combination",
                {"data_int": {"gt": 30, "lte": 70}},
                range(4, 8),
            ),
        ]
    )
    async def test_search_with_range_query(self, _, query_range, expected_ids):
        for i in range(0, 12):
            body = {
                "id": i,
                "timestamp": datetime.datetime(2009, 1, 1, 10, 5 * i, 0),
                "data_int": 10 * i,
            }
            await self.es.index(index="index_for_search", doc_type=DOC_TYPE, body=body)

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"range": query_range}},
        )

        self.assertEqual(len(expected_ids), response["hits"]["total"]["value"])
        hits = response["hits"]["hits"]
        self.assertEqual(set(expected_ids), {hit["_source"]["id"] for hit in hits})

    @parameterized.expand(
        [
            (
                "data_int (100, 200) no overlap",
                {"data_int": {"gt": 100, "lt": 200}},
                {"intersects": [], "within": [], "contains": []},
            ),
            (
                "data_int (1,3)",
                {"data_int": {"gt": 1, "lt": 3}},
                {"intersects": [0], "within": [], "contains": [0]},
            ),
            (
                "data_int (5,10) exclusive",
                {"data_int": {"gt": 5, "lt": 10}},
                {"intersects": [], "within": [], "contains": []},
            ),
            (
                "data_int (5,10] inclusive",
                {"data_int": {"gt": 5, "lte": 10}},
                {"intersects": [1], "within": [], "contains": []},
            ),
            (
                "data_int (3,6) overlapping",
                {"data_int": {"gt": 3, "lt": 6}},
                {"intersects": [0], "within": [], "contains": []},
            ),
            (
                "data_int [0,25] inclusive covers both ranges",
                {"data_int": {"gte": 0, "lte": 25}},
                {"intersects": [0, 1], "within": [0, 1], "contains": []},
            ),
            (
                "data_int (0,25) exclusive covers both ranges",
                {"data_int": {"gt": 0, "lt": 25}},
                {"intersects": [0, 1], "within": [1], "contains": []},
            ),
        ]
    )
    async def test_range_search_with_range_query(
        self, _, query_range, expected_ids_by_relationship
    ):
        for i in range(0, 2):
            body = {
                "id": i,
                "data_int": {
                    "gte": 10 * i,
                    "lte": (10 * i) + 5,
                },
            }
            await self.es.index(index="index_for_search", doc_type=DOC_TYPE, body=body)

        for relationship in ["contains", "intersects", "within"]:
            query_range[list(query_range.keys())[0]]["relation"] = relationship
            response = await self.es.search(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"query": {"range": query_range}},
            )

            expected_ids = expected_ids_by_relationship[relationship]

            hits = response["hits"]["hits"]
            found_ids = list(hit["_source"]["id"] for hit in hits)

            self.assertCountEqual(
                expected_ids, found_ids, msg=f"Relationship: {relationship}"
            )
            self.assertEqual(len(expected_ids), response["hits"]["total"]["value"])

    async def test_bucket_aggregation(self):
        data = [
            {"data_x": 1, "data_y": "a"},
            {"data_x": 1, "data_y": "a"},
            {"data_x": 2, "data_y": "a"},
            {"data_x": 2, "data_y": "b"},
            {"data_x": 3, "data_y": "b"},
        ]
        for body in data:
            await self.es.index(index="index_for_search", doc_type=DOC_TYPE, body=body)

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={
                "query": {"match_all": {}},
                "aggs": {
                    "stats": {
                        "composite": {
                            "sources": [{"data_x": {"terms": {"field": "data_x"}}}],
                            "size": 10000,
                        },
                        "aggs": {
                            "distinct_data_y": {"cardinality": {"field": "data_y"}}
                        },
                    }
                },
            },
        )

        expected = [
            {"key": {"data_x": 1}, "doc_count": 2},
            {"key": {"data_x": 2}, "doc_count": 2},
            {"key": {"data_x": 3}, "doc_count": 1},
        ]
        actual = response["aggregations"]["stats"]["buckets"]

        for x, y in zip(expected, actual):
            self.assertDictEqual(x["key"], y["key"])
            self.assertEqual(x["doc_count"], y["doc_count"])

    async def test_search_with_exists_query(self):
        for i in range(0, 10):
            await self.es.index(
                index="index_for_search",
                doc_type=DOC_TYPE,
                body={"data": {"x": {"y": i if i % 3 == 0 else None}}},
            )

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"bool": {"must": [{"exists": {"field": "data.x.y"}}]}}},
        )
        self.assertEqual(4, response["hits"]["total"]["value"])
        self.assertEqual(4, len(response["hits"]["hits"]))

        response = await self.es.search(
            index="index_for_search",
            doc_type=DOC_TYPE,
            body={"query": {"bool": {"must_not": [{"exists": {"field": "data.x.y"}}]}}},
        )
        self.assertEqual(6, response["hits"]["total"]["value"])
        self.assertEqual(6, len(response["hits"]["hits"]))
