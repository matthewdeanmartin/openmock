from unittest import TestCase
from unittest.mock import patch

from openmock import FakeOpenSearchServer
from openmock.web import main as web_main


class TestFakeOpenSearchServer(TestCase):
    def test_should_support_security_crud(self):
        server = FakeOpenSearchServer()

        user_result = server.put_user("alice", {"backend_roles": ["admin"]})
        role_result = server.put_role("admin", {"cluster_permissions": ["cluster_all"]})

        self.assertEqual("created", user_result["result"])
        self.assertEqual("created", role_result["result"])
        self.assertEqual(["admin"], server.get_user("alice")["alice"]["backend_roles"])
        self.assertEqual(
            ["cluster_all"],
            server.get_role("admin")["admin"]["cluster_permissions"],
        )

        patch_result = server.patch_user("alice", {"attributes": {"team": "demo"}})
        delete_result = server.delete_role("admin")

        self.assertEqual("updated", patch_result["result"])
        self.assertEqual(
            "demo", server.get_user("alice")["alice"]["attributes"]["team"]
        )
        self.assertEqual("deleted", delete_result["result"])
        self.assertIsNone(server.get_role("admin"))

    def test_should_apply_ingest_pipeline_during_index(self):
        server = FakeOpenSearchServer()
        server.put_pipeline(
            "normalize",
            {
                "processors": [
                    {"trim": {"field": "message"}},
                    {"lowercase": {"field": "message"}},
                    {"set": {"field": "flags.ingested", "value": True}},
                    {"convert": {"field": "count", "type": "integer"}},
                ]
            },
        )

        server.index_document(
            index="logs",
            body={"message": "  HELLO  ", "count": "3"},
            document_id="1",
            pipeline="normalize",
        )

        hit = server.search_documents(index="logs")["hits"]["hits"][0]
        self.assertEqual("hello", hit["_source"]["message"])
        self.assertEqual(3, hit["_source"]["count"])
        self.assertTrue(hit["_source"]["flags"]["ingested"])

    def test_should_simulate_pipeline(self):
        server = FakeOpenSearchServer()
        server.put_pipeline(
            "rename-message",
            {
                "processors": [
                    {"rename": {"field": "message", "target_field": "event.message"}}
                ]
            },
        )

        result = server.simulate_pipeline(
            body={"docs": [{"_source": {"message": "hello"}}]},
            pipeline_id="rename-message",
        )

        self.assertEqual(
            "hello",
            result["docs"][0]["doc"]["_source"]["event"]["message"],
        )

    def test_should_render_cat_formats(self):
        server = FakeOpenSearchServer()
        server.index_document(index="books", body={"title": "Docs"})

        cat_json = server.cat_indices(format_type="json")
        cat_text = server.cat_indices(format_type="text", verbose=True)

        self.assertEqual("books", cat_json[0]["index"])
        self.assertIn("index", cat_text)
        self.assertIn("books", cat_text)


class TestWebCli(TestCase):
    @patch("streamlit.web.bootstrap.run")
    def test_should_bootstrap_streamlit_from_cli(self, bootstrap_run):
        result = web_main([])

        self.assertEqual(0, result)
        bootstrap_run.assert_called_once()
        args, kwargs = bootstrap_run.call_args
        self.assertTrue(str(args[0]).replace("\\", "/").endswith("openmock/web.py"))
        self.assertFalse(args[1])
        self.assertEqual([], args[2])
        self.assertEqual({}, args[3])
        self.assertEqual({}, kwargs)
