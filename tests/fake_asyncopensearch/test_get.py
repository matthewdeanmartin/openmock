from opensearchpy.exceptions import NotFoundError

from tests import BODY, DOC_TYPE, INDEX_NAME, Testasyncopenmock


class TestGet(Testasyncopenmock):
    async def test_should_raise_notfounderror_when_nonindexed_id_is_used(self):
        with self.assertRaises(NotFoundError):
            await self.es.get(index=INDEX_NAME, id="1")

    async def test_should_not_raise_notfounderror_when_nonindexed_id_is_used_and_ignored(
        self,
    ):
        target_doc = await self.es.get(index=INDEX_NAME, id="1", ignore=404)
        self.assertFalse(target_doc.get("found"))

    async def test_should_not_raise_notfounderror_when_nonindexed_id_is_used_and_ignored_list(
        self,
    ):
        target_doc = await self.es.get(index=INDEX_NAME, id="1", ignore=(401, 404))
        self.assertFalse(target_doc.get("found"))

    async def test_should_get_document_with_id(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        document_id = data.get("_id")
        target_doc = await self.es.get(index=INDEX_NAME, id=document_id)

        expected = {
            "_type": "_doc",
            "_source": BODY,
            "_index": INDEX_NAME,
            "_version": 1,
            "found": True,
            "_id": document_id,
        }

        self.assertDictEqual(expected, target_doc)

    async def test_should_get_document_with_id_and_doc_type(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        document_id = data.get("_id")
        target_doc = await self.es.get(
            index=INDEX_NAME, id=document_id, doc_type=DOC_TYPE
        )

        expected = {
            "_type": "_doc",
            "_source": BODY,
            "_index": INDEX_NAME,
            "_version": 1,
            "found": True,
            "_id": document_id,
        }

        self.assertDictEqual(expected, target_doc)

    async def test_should_get_only_document_source_with_id(self):
        data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        document_id = data.get("_id")
        target_doc_source = await self.es.get_source(
            index=INDEX_NAME,
            # doc_type=DOC_TYPE,
            id=document_id,
        )

        self.assertEqual(target_doc_source, BODY)

    async def test_mget_get_several_documents_by_id(self):
        ids = []
        for _ in range(0, 10):
            data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
            ids.append(data.get("_id"))
        results = await self.es.mget(
            index=INDEX_NAME, body={"docs": [{"_id": id} for id in ids]}
        )
        self.assertEqual(len(results["docs"]), 10)
