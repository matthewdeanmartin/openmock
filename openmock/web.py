import json
import sys
from pathlib import Path
from typing import Any

from openmock.behaviour.server_failure import server_failure
from openmock.fake_server import FakeOpenSearchServer


def _streamlit_missing_message() -> str:
    return "Install the web extra to run the UI: pip install openmock[web]"


def _get_response_error(result: Any) -> str | None:
    if isinstance(result, dict) and result.get("status_code", 200) >= 400:
        return result.get("error", "Unexpected error")
    return None


def main(args: list[str] | None = None) -> int:
    try:
        # pylint: disable=import-outside-toplevel
        from streamlit.web import bootstrap
    except ImportError as exc:
        raise SystemExit(_streamlit_missing_message()) from exc

    cli_args = list(sys.argv[1:] if args is None else args)
    bootstrap.run(str(Path(__file__).resolve()), False, cli_args, {})
    return 0


# pylint: disable=too-many-statements
def website() -> None:
    try:
        # pylint: disable=import-outside-toplevel
        import streamlit as st
    except ImportError as exc:
        raise SystemExit(_streamlit_missing_message()) from exc

    st.set_page_config(page_title="Openmock Management Console", layout="wide")

    if "server" not in st.session_state:
        st.session_state.server = FakeOpenSearchServer()

    server = st.session_state.server
    es = server.es

    st.title("Openmock Management Console")

    # Sidebar for behaviors and global settings
    with st.sidebar:
        st.header("Behaviors")
        if st.toggle("Simulate Server Failure", value=server_failure.is_enabled()):
            server_failure.enable()
        else:
            server_failure.disable()

        st.divider()
        if st.button("Reset Openmock"):
            st.session_state.server = FakeOpenSearchServer()
            st.rerun()

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["Indices", "Search Sandbox", "Cluster Stats", "CAT", "Security", "Ingest"]
    )

    with tab1:
        st.header("Indices")
        # Accessing internal dict for visualization
        docs_dict = es._FakeIndicesClient__documents_dict

        if not docs_dict:
            st.info("No indices created yet.")
        else:
            for index_name, docs in docs_dict.items():
                with st.expander(f"Index: {index_name} ({len(docs)} documents)"):
                    st.write("Documents:")
                    st.json(docs)

        st.divider()
        st.subheader("Create Index / Add Document")
        with st.form("add_doc"):
            idx = st.text_input("Index Name", value="test-index")
            doc_id = st.text_input("Document ID (optional)")
            pipelines = ["(none)", *sorted(server._pipelines.keys())]
            selected_pipeline = st.selectbox("Ingest Pipeline", options=pipelines)
            doc_body = st.text_area("Document JSON", value='{"foo": "bar", "count": 1}')
            submit = st.form_submit_button("Index Document")

            if submit:
                try:
                    body = json.loads(doc_body)
                    res = server.index_document(
                        index=idx,
                        body=body,
                        document_id=doc_id if doc_id else None,
                        pipeline=(
                            None if selected_pipeline == "(none)" else selected_pipeline
                        ),
                    )
                    error = _get_response_error(res)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Document indexed: {res.get('_id')}")
                        st.rerun()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    st.error(f"Error: {e}")

    with tab2:
        st.header("Search Sandbox")
        search_index = st.text_input(
            "Search Index (comma separated or * for all)", value="*"
        )
        search_query = st.text_area(
            "Search Query (JSON)",
            value='{"query": {"match_all": {}}, "aggs": {"my_agg": {"terms": {"field": "category"}}}}',
        )

        if st.button("Execute Search"):
            try:
                query = json.loads(search_query)
                index = None if search_index in {"", "*"} else search_index
                res = server.search_documents(index=index, body=query)
                st.subheader("Response")

                error = _get_response_error(res)
                if error:
                    st.error(error)
                elif "aggregations" in res:
                    st.write("Aggregations:")
                    st.json(res["aggregations"])
                    st.write("Hits:")
                    st.json(res)
                else:
                    st.write("Hits:")
                    st.json(res)
            except Exception as e:  # pylint: disable=broad-exception-caught
                st.error(f"Error: {e}")

    with tab3:
        st.header("Cluster Status")
        try:
            health = server.health()
            st.write("Health Status:")
            error = _get_response_error(health)
            if error:
                st.error(error)
            else:
                st.json(health)

            info = server.info()
            st.write("Cluster Info:")
            error = _get_response_error(info)
            if error:
                st.error(error)
            else:
                st.json(info)
        except Exception as e:  # pylint: disable=broad-exception-caught
            st.error(f"Error: {e}")

    with tab4:
        st.header("CAT")
        cat_view = st.radio("Format", ["table", "json"], horizontal=True)
        cat_endpoint = st.selectbox("Endpoint", ["indices", "count"])
        format_type = "json" if cat_view == "json" else "text"
        try:
            if cat_endpoint == "indices":
                payload = server.cat_indices(
                    format_type=format_type, verbose=cat_view == "table"
                )
            else:
                payload = server.cat_count(
                    format_type=format_type, verbose=cat_view == "table"
                )

            if isinstance(payload, str):
                st.code(payload or "(empty)", language="text")
            else:
                st.json(payload)
        except Exception as e:  # pylint: disable=broad-exception-caught
            st.error(f"Error: {e}")

    with tab5:
        st.header("Security")
        st.caption(
            "Permissive fake CRUD only: users and roles can be created, listed, updated, "
            "and deleted, but no authentication or authorization checks are enforced."
        )
        users_tab, roles_tab = st.tabs(["Users", "Roles"])

        with users_tab:
            st.subheader("Current Users")
            st.json(server._users)

            with st.form("upsert_user"):
                username = st.text_input("Username", value="demo-user")
                user_body = st.text_area(
                    "User JSON",
                    value=(
                        '{"password":"not-checked","backend_roles":["admin"],'
                        '"attributes":{"team":"demo"}}'
                    ),
                )
                submit_user = st.form_submit_button("Create / Update User")
                if submit_user:
                    try:
                        result = server.put_user(username, json.loads(user_body))
                        error = _get_response_error(result)
                        if error:
                            st.error(error)
                        else:
                            st.success(result["message"])
                            st.rerun()
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        st.error(f"Error: {e}")

            delete_user = st.text_input("Delete Username", value="")
            if st.button("Delete User"):
                result = server.delete_user(delete_user)
                if result is None:
                    st.error(f"User '{delete_user}' not found.")
                else:
                    st.success(result["message"])
                    st.rerun()

        with roles_tab:
            st.subheader("Current Roles")
            st.json(server._roles)

            with st.form("upsert_role"):
                role_name = st.text_input("Role Name", value="demo-role")
                role_body = st.text_area(
                    "Role JSON",
                    value=(
                        '{"cluster_permissions":["cluster_all"],'
                        '"index_permissions":[{"index_patterns":["*"],'
                        '"allowed_actions":["read"]}]}'
                    ),
                )
                submit_role = st.form_submit_button("Create / Update Role")
                if submit_role:
                    try:
                        result = server.put_role(role_name, json.loads(role_body))
                        error = _get_response_error(result)
                        if error:
                            st.error(error)
                        else:
                            st.success(result["message"])
                            st.rerun()
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        st.error(f"Error: {e}")

            delete_role = st.text_input("Delete Role", value="")
            if st.button("Delete Role"):
                result = server.delete_role(delete_role)
                if result is None:
                    st.error(f"Role '{delete_role}' not found.")
                else:
                    st.success(result["message"])
                    st.rerun()

    with tab6:
        st.header("Ingest")
        st.caption(
            "Pipelines are fake and in-memory. Supported processors include set, rename, "
            "remove, append, lowercase, uppercase, trim, split, convert, gsub, and json."
        )
        st.subheader("Current Pipelines")
        st.json(server._pipelines)

        with st.form("upsert_pipeline"):
            pipeline_id = st.text_input("Pipeline ID", value="normalize-message")
            pipeline_body = st.text_area(
                "Pipeline JSON",
                value=(
                    '{"description":"Normalize message fields","processors":['
                    '{"trim":{"field":"message"}},'
                    '{"lowercase":{"field":"message"}},'
                    '{"set":{"field":"labels.ingested","value":true}}]}'
                ),
                height=180,
            )
            submit_pipeline = st.form_submit_button("Create / Update Pipeline")
            if submit_pipeline:
                try:
                    result = server.put_pipeline(pipeline_id, json.loads(pipeline_body))
                    error = _get_response_error(result)
                    if error:
                        st.error(error)
                    else:
                        st.success(result["message"])
                        st.rerun()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    st.error(f"Error: {e}")

        pipeline_ids = sorted(server._pipelines.keys())
        if pipeline_ids:
            selected_pipeline = st.selectbox(
                "Pipeline to Simulate", options=pipeline_ids
            )
            simulation_body = st.text_area(
                "Simulation JSON",
                value='{"docs":[{"_source":{"message":"  HELLO WORLD  ","count":"3"}}]}',
                height=140,
            )
            if st.button("Simulate Pipeline"):
                try:
                    result = server.simulate_pipeline(
                        body=json.loads(simulation_body), pipeline_id=selected_pipeline
                    )
                    error = _get_response_error(result)
                    if error:
                        st.error(error)
                    else:
                        st.json(result)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    st.error(f"Error: {e}")
        else:
            st.info(
                "Create a pipeline to simulate it or use it while indexing documents."
            )

        delete_pipeline = st.text_input("Delete Pipeline", value="")
        if st.button("Delete Pipeline"):
            result = server.delete_pipeline(delete_pipeline)
            if result is None:
                st.error(f"Pipeline '{delete_pipeline}' not found.")
            else:
                st.success(result["message"])
                st.rerun()


if __name__ == "__main__":
    website()
