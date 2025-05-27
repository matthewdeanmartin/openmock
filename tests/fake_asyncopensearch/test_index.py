from tests import BODY, DOC_TYPE, INDEX_NAME, Testasyncopenmock

UPDATED_BODY = {"author": "vrcmarcos", "text": "Updated Text"}


class TestIndex(Testasyncopenmock):
    async def test_should_index_document(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        # self.assertEqual(DOC_TYPE, data.get("_type"))
        self.assertTrue(data.get("created"))
        self.assertEqual(1, data.get("_version"))
        self.assertEqual(INDEX_NAME, data.get("_index"))
        self.assertEqual("created", data.get("result"))

    async def test_should_index_document_without_doc_type(self):
        data = await self.es.index(index=INDEX_NAME, body=BODY)

        self.assertEqual("_doc", data.get("_type"))
        self.assertTrue(data.get("created"))
        self.assertEqual(1, data.get("_version"))
        self.assertEqual(INDEX_NAME, data.get("_index"))

    # https://github.com/elastic/elasticsearch-py/issues/846
    # def test_doc_type_can_be_list(self):
    #     doc_types = ["1_idx", "2_idx", "3_idx"]
    #     count_per_doc_type = 3
    #
    #     for doc_type in doc_types:
    #         for _ in range(count_per_doc_type):
    #             await self.es.index(index=INDEX_NAME, doc_type=doc_type, body={})
    #
    #     result = await self.es.search(doc_type=[doc_types[0]])
    #     self.assertEqual(
    #         count_per_doc_type, result.get("hits").get("total").get("value")
    #     )
    #
    #     result = await self.es.search(doc_type=doc_types[:2])
    #     self.assertEqual(
    #         count_per_doc_type * 2, result.get("hits").get("total").get("value")
    #     )

    async def test_update_existing_doc(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
        document_id = data.get("_id")
        await self.es.index(
            index=INDEX_NAME, id=document_id, doc_type=DOC_TYPE, body=UPDATED_BODY
        )
        target_doc = await self.es.get(index=INDEX_NAME, id=document_id)

        expected = {
            "_type": "_doc",
            "_source": UPDATED_BODY,
            "_index": INDEX_NAME,
            "_version": 2,
            "found": True,
            "_id": document_id,
        }

        self.assertDictEqual(expected, target_doc)

    async def test_update_by_query(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
        document_id = data.get("_id")
        new_author = "kimchy2"
        await self.es.update_by_query(
            index=INDEX_NAME,
            body={
                "query": {
                    "match": {"author": "kimchy"},
                },
                "script": {
                    "source": "ctx._source.author = params.author",
                    "params": {"author": new_author},
                },
            },
        )
        target_doc = await self.es.get(index=INDEX_NAME, id=document_id)
        self.assertEqual(target_doc["_source"]["author"], new_author)
