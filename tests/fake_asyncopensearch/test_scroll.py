from tests import BODY, DOC_TYPE, INDEX_NAME, Testasyncopenmock


class TestScroll(Testasyncopenmock):
    async def test_scrolling(self):
        for _ in range(100):
            await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        result = await self.es.search(
            index=INDEX_NAME, params={"scroll": "1m", "size": 30}
        )
        self.__assert_scroll(result, 30)

        for _ in range(2):
            result = await self.es.scroll(
                scroll_id=result.get("_scroll_id"), scroll="1m"
            )
            self.__assert_scroll(result, 30)

        result = await self.es.scroll(scroll_id=result.get("_scroll_id"), scroll="1m")
        self.__assert_scroll(result, 10)

    def __assert_scroll(self, result, expected_scroll_hits):
        hits = result.get("hits")

        self.assertNotEqual(None, result.get("_scroll_id", None))
        self.assertEqual(expected_scroll_hits, len(hits.get("hits")))
        self.assertEqual(100, hits.get("total").get("value"))
