from opensearchpy.exceptions import NotFoundError

from tests import BODY, DOC_TYPE, INDEX_NAME, Testasyncopenmock


class TestSuggest(Testasyncopenmock):
    async def test_should_raise_notfounderror_when_nonindexed_id_is_used_for_suggest(
        self,
    ):
        with self.assertRaises(NotFoundError):
            await self.es.suggest(body={}, index=INDEX_NAME)

    async def test_should_return_suggestions(self):
        await self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
        suggestion_body = {
            "suggestion-string": {"text": "test_text", "term": {"field": "string"}},
            "suggestion-id": {"text": 1234567, "term": {"field": "id"}},
        }
        suggestion = self.es.suggest(body=suggestion_body, index=INDEX_NAME)
        self.assertIsNotNone(suggestion)
        self.assertDictEqual(
            {
                "suggestion-string": [
                    {
                        "text": "test_text",
                        "length": 1,
                        "options": [
                            {"text": "test_text_suggestion", "freq": 1, "score": 1.0}
                        ],
                        "offset": 0,
                    }
                ],
                "suggestion-id": [
                    {
                        "text": 1234567,
                        "length": 1,
                        "options": [{"text": 1234568, "freq": 1, "score": 1.0}],
                        "offset": 0,
                    }
                ],
            },
            suggestion,
        )
