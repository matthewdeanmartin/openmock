from tests import DOC_TYPE, Testasyncopenmock


class TestCount(Testasyncopenmock):
    async def test_should_return_count_for_indexed_documents_on_index(self):
        index_quantity = 0
        for i in range(0, index_quantity):
            await self.es.index(
                index=f"index_{i}",
                doc_type=DOC_TYPE,
                body={"data": f"test_{i}"},
            )

        count = await self.es.count()
        self.assertEqual(index_quantity, count.get("count"))

    async def test_should_count_in_multiple_indexes(self):
        await self.es.index(index="groups", doc_type="groups", body={"budget": 1000})
        await self.es.index(index="users", doc_type="users", body={"name": "toto"})
        await self.es.index(index="pcs", doc_type="pcs", body={"model": "macbook"})

        result = await self.es.count(index=["users", "pcs"])
        self.assertEqual(2, result.get("count"))

    async def test_should_count_with_empty_doc_types(self):
        await self.es.index(
            index="index",
            # doc_type=DOC_TYPE,
            body={"data": "test"},
        )
        count = await self.es.count(
            # doc_type=[]
        )
        self.assertEqual(1, count.get("count"))

    async def test_should_return_skipped_shards(self):
        await self.es.index(
            index="index",
            # doc_type=DOC_TYPE,
            body={"data": "test"},
        )
        count = await self.es.count(
            # doc_type=[]
        )
        self.assertEqual(0, count.get("_shards").get("skipped"))

    async def test_should_count_with_doc_types(self):
        await self.es.index(
            index="index",
            # doc_type=DOC_TYPE,
            body={"data": "test1"},
        )
        await self.es.index(
            index="index",
            # doc_type="different-doc-type",
            body={"data": "test2"},
        )
        count = await self.es.count(
            # doc_type=DOC_TYPE
        )
        # well not anymore, doc_type is deprecated I think
        self.assertEqual(2, count.get("count"))
