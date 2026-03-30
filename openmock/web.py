import streamlit as st
import json
from openmock import FakeOpenSearch
from openmock.behaviour.server_failure import server_failure

st.set_page_config(page_title="Openmock Management Console", layout="wide")

if "es" not in st.session_state:
    st.session_state.es = FakeOpenSearch()

es = st.session_state.es

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
        st.session_state.es = FakeOpenSearch()
        st.rerun()

# Main Tabs
tab1, tab2, tab3 = st.tabs(["Indices", "Search Sandbox", "Cluster Stats"])

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
        doc_body = st.text_area("Document JSON", value='{"foo": "bar", "count": 1}')
        submit = st.form_submit_button("Index Document")
        
        if submit:
            try:
                body = json.loads(doc_body)
                res = es.index(index=idx, body=body, id=doc_id if doc_id else None)
                st.success(f"Document indexed: {res.get('_id')}")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

with tab2:
    st.header("Search Sandbox")
    search_index = st.text_input("Search Index (comma separated or * for all)", value="*")
    search_query = st.text_area("Search Query (JSON)", value='{"query": {"match_all": {}}, "aggs": {"my_agg": {"terms": {"field": "category"}}}}')
    
    if st.button("Execute Search"):
        try:
            query = json.loads(search_query)
            res = es.search(index=search_index, body=query)
            st.subheader("Response")
            
            if "aggregations" in res:
                st.write("Aggregations:")
                st.json(res["aggregations"])
                
            st.write("Hits:")
            st.json(res)
        except Exception as e:
            st.error(f"Error: {e}")

with tab3:
    st.header("Cluster Status")
    try:
        health = es.cluster.health()
        st.write("Health Status:")
        st.json(health)
        
        info = es.info()
        st.write("Cluster Info:")
        st.json(info)
    except Exception as e:
        st.error(f"Error: {e}")
