import json

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response

from openmock.fake_server import FakeOpenSearchServer

app = FastAPI(title="Openmock REST Bridge")
server = FakeOpenSearchServer()


async def _read_json_body(request: Request, default):
    body = await request.body()
    if not body:
        return default
    return json.loads(body)


def _cat_response(payload):
    if isinstance(payload, str):
        return Response(content=payload, media_type="text/plain")
    return payload


def _parse_cat_headers(raw_headers: str | None):
    if not raw_headers:
        return None
    return [header.strip() for header in raw_headers.split(",") if header.strip()]


@app.get("/")
def info():
    return server.info()


@app.get("/_cluster/health")
def health():
    return server.health()


@app.post("/{index}/_doc")
@app.put("/{index}/_doc/{document_id}")
async def index_doc(index: str, request: Request, document_id: str | None = None):
    body = await _read_json_body(request, {})
    pipeline = request.query_params.get("pipeline")
    return server.index_document(
        index=index, body=body, document_id=document_id, pipeline=pipeline
    )


@app.post("/{index}/_create/{document_id}")
@app.put("/{index}/_create/{document_id}")
async def create_doc(index: str, document_id: str, request: Request):
    body = await _read_json_body(request, {})
    pipeline = request.query_params.get("pipeline")
    return server.create_document(
        index=index, body=body, document_id=document_id, pipeline=pipeline
    )


@app.post("/{index}/_create")
async def create_doc_without_id(index: str, request: Request):
    body = await _read_json_body(request, {})
    pipeline = request.query_params.get("pipeline")
    return server.index_document(index=index, body=body, pipeline=pipeline)


@app.api_route("/{index}/_search", methods=["GET", "POST"])
async def search(index: str, request: Request):
    body = await _read_json_body(request, {"query": {"match_all": {}}})
    return server.search_documents(index=index, body=body)


@app.get("/{index}/_count")
@app.get("/_count")
async def count(request: Request, index: str | None = None):
    body = await _read_json_body(request, None)
    return server.count_documents(index=index, body=body)


@app.get("/_cat/indices")
async def cat_indices(request: Request):
    payload = server.cat_indices(
        format_type=request.query_params.get("format", "text"),
        verbose=request.query_params.get("v", "").lower() == "true",
        headers=_parse_cat_headers(request.query_params.get("h")),
    )
    return _cat_response(payload)


@app.get("/_cat/count")
async def cat_count(request: Request):
    payload = server.cat_count(
        format_type=request.query_params.get("format", "text"),
        verbose=request.query_params.get("v", "").lower() == "true",
        headers=_parse_cat_headers(request.query_params.get("h")),
    )
    return _cat_response(payload)


@app.get("/_plugins/_security/api/internalusers")
@app.get("/_opendistro/_security/api/internalusers")
def list_users():
    return server.list_users()


@app.get("/_plugins/_security/api/internalusers/{username}")
@app.get("/_opendistro/_security/api/internalusers/{username}")
def get_user(username: str):
    result = server.get_user(username)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
    return result


@app.put("/_plugins/_security/api/internalusers/{username}")
@app.put("/_opendistro/_security/api/internalusers/{username}")
async def put_user(username: str, request: Request):
    body = await _read_json_body(request, {})
    return server.put_user(username, body)


@app.patch("/_plugins/_security/api/internalusers/{username}")
@app.patch("/_opendistro/_security/api/internalusers/{username}")
async def patch_user(username: str, request: Request):
    body = await _read_json_body(request, {})
    result = server.patch_user(username, body)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
    return result


@app.delete("/_plugins/_security/api/internalusers/{username}")
@app.delete("/_opendistro/_security/api/internalusers/{username}")
def delete_user(username: str):
    result = server.delete_user(username)
    if result is None:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found.")
    return result


@app.get("/_plugins/_security/api/roles")
@app.get("/_opendistro/_security/api/roles")
def list_roles():
    return server.list_roles()


@app.get("/_plugins/_security/api/roles/{role_name}")
@app.get("/_opendistro/_security/api/roles/{role_name}")
def get_role(role_name: str):
    result = server.get_role(role_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found.")
    return result


@app.put("/_plugins/_security/api/roles/{role_name}")
@app.put("/_opendistro/_security/api/roles/{role_name}")
async def put_role(role_name: str, request: Request):
    body = await _read_json_body(request, {})
    return server.put_role(role_name, body)


@app.patch("/_plugins/_security/api/roles/{role_name}")
@app.patch("/_opendistro/_security/api/roles/{role_name}")
async def patch_role(role_name: str, request: Request):
    body = await _read_json_body(request, {})
    result = server.patch_role(role_name, body)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found.")
    return result


@app.delete("/_plugins/_security/api/roles/{role_name}")
@app.delete("/_opendistro/_security/api/roles/{role_name}")
def delete_role(role_name: str):
    result = server.delete_role(role_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Role '{role_name}' not found.")
    return result


@app.get("/_ingest/pipeline")
@app.get("/_ingest/pipeline/{pipeline_id}")
def get_pipeline(pipeline_id: str | None = None):
    result = server.get_pipeline(pipeline_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline '{pipeline_id}' not found."
        )
    return result


@app.put("/_ingest/pipeline/{pipeline_id}")
async def put_pipeline(pipeline_id: str, request: Request):
    body = await _read_json_body(request, {})
    return server.put_pipeline(pipeline_id, body)


@app.delete("/_ingest/pipeline/{pipeline_id}")
def delete_pipeline(pipeline_id: str):
    result = server.delete_pipeline(pipeline_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail=f"Pipeline '{pipeline_id}' not found."
        )
    return result


@app.post("/_ingest/pipeline/{pipeline_id}/_simulate")
@app.post("/_ingest/pipeline/_simulate")
async def simulate_pipeline(request: Request, pipeline_id: str | None = None):
    body = await _read_json_body(request, {})
    return server.simulate_pipeline(body=body, pipeline_id=pipeline_id)


def main():
    print("Openmock REST Bridge running on http://localhost:9201")
    print("This allows non-python tools to talk to the fake.")
    uvicorn.run(app, host="127.0.0.1", port=9201)


if __name__ == "__main__":
    main()
