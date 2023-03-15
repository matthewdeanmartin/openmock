# -*- coding: utf-8 -*-

from tests import Testopenmock, INDEX_NAME, DOC_TYPE, BODY
from opensearchpy.exceptions import ConflictError

UPDATED_BODY = {"author": "vrcmarcos", "text": "Updated Text"}


class TestCreate(Testopenmock):
    def test_should_create_document(self):
        data = self.es.create(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)

        self.assertEqual(DOC_TYPE, data.get("_type"))
        self.assertTrue(data.get("created"))
        self.assertEqual(1, data.get("_version"))
        self.assertEqual(INDEX_NAME, data.get("_index"))
        self.assertEqual("created", data.get("result"))

    def test_should_index_document_without_doc_type(self):
        data = self.es.index(index=INDEX_NAME, body=BODY)

        self.assertEqual("_doc", data.get("_type"))
        self.assertTrue(data.get("created"))
        self.assertEqual(1, data.get("_version"))
        self.assertEqual(INDEX_NAME, data.get("_index"))

    def test_doc_type_can_be_list(self):
        doc_types = ["1_idx", "2_idx", "3_idx"]
        count_per_doc_type = 3

        for doc_type in doc_types:
            for _ in range(count_per_doc_type):
                self.es.index(index=INDEX_NAME, doc_type=doc_type, body={})

        result = self.es.search(doc_type=[doc_types[0]])
        self.assertEqual(
            count_per_doc_type, result.get("hits").get("total").get("value")
        )

        result = self.es.search(doc_type=doc_types[:2])
        self.assertEqual(
            count_per_doc_type * 2, result.get("hits").get("total").get("value")
        )

    def test_should_throw_error_if_doc_exists(self):
        data = self.es.index(index=INDEX_NAME, doc_type=DOC_TYPE, body=BODY)
        document_id = data.get("_id")
        self.assertRaises(ConflictError, self.es.create, INDEX_NAME, UPDATED_BODY, DOC_TYPE, document_id)
