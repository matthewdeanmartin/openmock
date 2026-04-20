import unittest

import opensearchpy
from opensearchpy import Date, Document, Index, Text
from opensearchpy.exceptions import RequestError
from opensearchpy.helpers import analysis

from openmock import openmock


class Post(Document):
    title = Text(analyzer=analysis.analyzer("my_analyzer", tokenizer="keyword"))
    published_from = Date()


class TestOpenSearchPyCompatibility(unittest.TestCase):
    @openmock
    def setUp(self):
        self.client = opensearchpy.OpenSearch(
            hosts=[{"host": "localhost", "port": 9200}]
        )

    def test_index_with_slash(self) -> None:
        index_name = "movies/shmovies"
        with self.assertRaises(RequestError) as e:
            self.client.indices.create(index=index_name)
        self.assertEqual(e.exception.status_code, 400)
        self.assertEqual(e.exception.error, "invalid_index_name_exception")
        self.assertIn("must not contain the following characters", e.exception.args[2])

    def test_indices_lifecycle_english(self) -> None:
        index_name = "movies"

        index_create_result = self.client.indices.create(index=index_name)
        self.assertTrue(index_create_result["acknowledged"])
        self.assertEqual(index_name, index_create_result["index"])

        document = {"name": "Solaris", "director": "Andrei Tartakovsky", "year": "2011"}
        id = "solaris@2011"
        doc_insert_result = self.client.index(
            index=index_name, body=document, id=id, refresh=True
        )
        self.assertEqual("created", doc_insert_result["result"])
        self.assertEqual(index_name, doc_insert_result["_index"])
        self.assertEqual(id, doc_insert_result["_id"])

        doc_delete_result = self.client.delete(index=index_name, id=id)
        self.assertEqual("deleted", doc_delete_result["result"])
        self.assertEqual(index_name, doc_delete_result["_index"])
        self.assertEqual(id, doc_delete_result["_id"])

        index_delete_result = self.client.indices.delete(index=index_name)
        self.assertTrue(index_delete_result["acknowledged"])

    def test_indices_lifecycle_russian(self) -> None:
        index_name = "кино"
        index_create_result = self.client.indices.create(index=index_name)
        self.assertTrue(index_create_result["acknowledged"])
        self.assertEqual(index_name, index_create_result["index"])

        document = {"название": "Солярис", "автор": "Андрей Тарковский", "год": "2011"}
        id = "соларис@2011"
        doc_insert_result = self.client.index(
            index=index_name, body=document, id=id, refresh=True
        )
        self.assertEqual("created", doc_insert_result["result"])
        self.assertEqual(index_name, doc_insert_result["_index"])
        self.assertEqual(id, doc_insert_result["_id"])

        doc_delete_result = self.client.delete(index=index_name, id=id)
        self.assertEqual("deleted", doc_delete_result["result"])
        self.assertEqual(index_name, doc_delete_result["_index"])
        self.assertEqual(id, doc_delete_result["_id"])

        index_delete_result = self.client.indices.delete(index=index_name)
        self.assertTrue(index_delete_result["acknowledged"])

    def test_indices_analyze(self) -> None:
        self.client.indices.analyze(body='{"text": "привет"}')

    def test_bulk_works_with_string_body(self) -> None:
        docs = '{ "index" : { "_index" : "bulk_test_index", "_id" : "1" } }\n{"answer": 42}'
        result = self.client.bulk(body=docs, refresh=True)
        self.assertFalse(result["errors"])
        self.assertEqual(1, len(result["items"]))
        self.assertEqual("created", result["items"][0]["index"]["result"])
        self.assertEqual("bulk_test_index", result["items"][0]["index"]["_index"])
        self.assertEqual("1", result["items"][0]["index"]["_id"])
        self.assertEqual(201, result["items"][0]["index"]["status"])

    def test_bulk_works_with_bytestring_body(self) -> None:
        docs = b'{ "index" : { "_index" : "bulk_test_index", "_id" : "2" } }\n{"answer": 42}'
        response = self.client.bulk(body=docs)

        self.assertFalse(response["errors"])
        self.assertEqual(1, len(response["items"]))

    def test_bulk_works_with_delete(self) -> None:
        docs = '{ "index" : { "_index" : "bulk_test_index", "_id" : "1" } }\n{"answer": 42}\n{ "delete" : { "_index" : "bulk_test_index", "_id": "1" } }'
        response = self.client.bulk(body=docs)

        self.assertFalse(response["errors"])
        self.assertEqual(2, len(response["items"]))

        # Check insertion status
        self.assertEqual(201, response["items"][0]["index"]["status"])
        # Check deletion status
        self.assertEqual(200, response["items"][1]["delete"]["status"])

    def test_simple_search(self) -> None:
        index_name = "search_test_index"
        self.client.indices.create(index=index_name)
        self.client.index(
            index=index_name,
            body={"name": "test_doc_1", "value": 1},
            id="1",
            refresh=True,
        )
        self.client.index(
            index=index_name,
            body={"name": "test_doc_2", "value": 2},
            id="2",
            refresh=True,
        )

        result = self.client.search(
            index=index_name, body={"query": {"match": {"name": "test_doc_1"}}}
        )
        self.assertEqual(1, result["hits"]["total"]["value"])
        self.assertEqual("test_doc_1", result["hits"]["hits"][0]["_source"]["name"])

    def test_close_doesnt_break_client(self) -> None:
        self.client.cluster.health()
        self.client.close()
        self.client.cluster.health()

    def test_with_doesnt_break_client(self) -> None:
        for _ in range(2):
            with self.client as client:
                client.cluster.health()

    def test_index_exists(self) -> None:
        self.client.indices.create(index="git")
        assert Index("git", using=self.client).exists()
        assert not Index("not-there", using=self.client).exists()

    def test_index_can_be_created_with_settings_and_mappings(self) -> None:
        i = Index(name="test-blog", using=self.client)
        i.document(Post)
        i.settings(number_of_replicas=0, number_of_shards=1)
        i.create()

        expected_mapping = {
            "test-blog": {
                "mappings": {
                    "properties": {
                        "title": {"type": "text", "analyzer": "my_analyzer"},
                        "published_from": {"type": "date"},
                    }
                }
            }
        }
        self.assertEqual(
            expected_mapping, self.client.indices.get_mapping(index="test-blog")
        )

        settings = self.client.indices.get_settings(index="test-blog")
        assert settings["test-blog"]["settings"]["index"]["number_of_replicas"] == "0"
        assert settings["test-blog"]["settings"]["index"]["number_of_shards"] == "1"


if __name__ == "__main__":
    unittest.main()
