from tests import BODY, DOC_TYPE, INDEX_NAME, Testasyncopenmock


class TestExists(Testasyncopenmock):
    async def test_should_return_exists_false_if_nonindexed_id_is_used(self):
        self.assertFalse(
            await self.es.exists(index=INDEX_NAME, doc_type=DOC_TYPE, id=1)
        )

        async def test_should_return_exists_true_if_indexed_id_is_used(self):
            data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
            document_id = data.get("_id")
            self.assertTrue(
                await self.es.exists(
                    index=INDEX_NAME, doc_type=DOC_TYPE, id=document_id
                )
            )

        async def test_should_return_exists_true_if_index_id_matches_and_doctype_none(
            self,
        ):
            data = await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
            document_id = data.get("_id")
            self.assertTrue(await self.es.exists(index=INDEX_NAME, id=document_id))
