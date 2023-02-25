# -*- coding: utf-8 -*-
from opensearchpy.exceptions import NotFoundError, RequestError

from tests import Testopenmock, INDEX_NAME, BODY

UPDATED_BODY = {"author": "schenkd", "text": "Updated Text"}


class TestUpdate(Testopenmock):
    def test_update_document(self):
        new_document = self.es.index(index=INDEX_NAME, body=BODY)
        updated_document = self.es.update(
            index=INDEX_NAME, id=new_document.get("_id"), body={"doc": UPDATED_BODY}
        )

        self.assertEqual(
            new_document.get("_version") + 1, updated_document.get("_version")
        )
        self.assertEqual(INDEX_NAME, updated_document.get("_index"))
        self.assertEqual("updated", updated_document.get("result"))

        check_document = self.es.get(index=INDEX_NAME, id=new_document.get("_id"))
        self.assertEqual(
            check_document.get("_source", {}).get("author"), UPDATED_BODY["author"]
        )

    def test_update_document_not_found(self):
        with self.assertRaises(NotFoundError):
            self.es.update(
                index=INDEX_NAME, id="not-a-real-id", body={"doc": UPDATED_BODY}
            )

    def test_update_document_wrong_body(self):
        with self.assertRaises(RequestError):
            self.es.update(index=INDEX_NAME, id="not-a-real-id", body={"key": "value"})

        with self.assertRaises(RequestError):
            self.es.update(index=INDEX_NAME, id="not-a-real-id", body={})

        with self.assertRaises(RequestError):
            self.es.update(
                index=INDEX_NAME, id="not-a-real-id", body={"doc": {}, "script": {}}
            )

    def test_update_document_script_not_implemented(self):
        new_document = self.es.index(index=INDEX_NAME, body=BODY)

        with self.assertRaises(NotImplementedError):
            self.es.update(
                index=INDEX_NAME, id=new_document.get("_id"), body={"script": {}}
            )
