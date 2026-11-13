"""Exercise the REST bridge through HTTP, including previously untested routes."""

import pytest
from fastapi.testclient import TestClient

from openmock import rest_bridge
from openmock.fake_server import FakeOpenSearchServer


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(rest_bridge, "server", FakeOpenSearchServer())
    with TestClient(rest_bridge.app) as transport:
        yield transport


@pytest.mark.parametrize(
    "resource,name",
    [
        ("/_plugins/_security/api/internalusers", "alice"),
        ("/_opendistro/_security/api/internalusers", "alice"),
        ("/_plugins/_security/api/roles", "reader"),
        ("/_opendistro/_security/api/roles", "reader"),
    ],
)
def test_security_resource_lifecycle(client, resource, name):
    path = f"{resource}/{name}"
    assert client.get(path).status_code == 404
    assert client.patch(path, json={}).status_code == 404
    assert client.delete(path).status_code == 404
    assert client.put(path, json={"description": "original"}).status_code == 200
    assert name in client.get(resource).json()
    assert name in client.get(path).json()
    assert client.patch(path, json={"description": "updated"}).status_code == 200
    assert client.get(path).json()[name]["description"] == "updated"
    assert client.delete(path).status_code == 200
    assert client.get(path).status_code == 404


def test_pipeline_and_document_routes(client):
    path = "/_ingest/pipeline/stamp"
    assert client.get(path).status_code == 404
    assert client.delete(path).status_code == 404
    assert (
        client.put(
            path, json={"processors": [{"set": {"field": "kind", "value": "event"}}]}
        ).status_code
        == 200
    )
    assert "stamp" in client.get("/_ingest/pipeline").json()
    assert "stamp" in client.get(path).json()
    simulation = client.post(
        path + "/_simulate", json={"docs": [{"_source": {}}]}
    ).json()
    assert simulation["docs"][0]["doc"]["_source"]["kind"] == "event"
    assert (
        client.post(
            "/_ingest/pipeline/_simulate",
            json={"pipeline": {"processors": []}, "docs": []},
        ).status_code
        == 200
    )
    assert (
        client.put("/events/_doc/one?pipeline=stamp", json={"n": 1}).status_code == 200
    )
    assert client.post("/events/_doc", json={"n": 2}).status_code == 200
    assert client.put("/events/_create/three", json={"n": 3}).status_code == 200
    assert client.post("/events/_create", json={"n": 4}).status_code == 200
    assert (
        client.post(
            "/events/_search", json={"query": {"term": {"kind": "event"}}}
        ).json()["hits"]["total"]["value"]
        == 1
    )
    assert client.get("/events/_search").json()["hits"]["total"]["value"] == 4
    for endpoint in ("/events/_count", "/_count"):
        assert client.get(endpoint).json()["count"] == 4
        assert (
            client.post(endpoint, json={"query": {"term": {"kind": "event"}}}).json()[
                "count"
            ]
            == 1
        )
    assert client.get("/").json()["version"]
    assert client.get("/_cluster/health").json()["status"] in {"green", "yellow"}
    for endpoint in ("/_cat/indices", "/_cat/count"):
        assert client.get(endpoint).headers["content-type"].startswith("text/plain")
        assert isinstance(
            client.get(endpoint + "?format=json&v=true&h=index,count").json(), list
        )
    assert client.delete(path).status_code == 200


@pytest.mark.parametrize("body", [b"{", b"\xff"])
def test_invalid_json_returns_client_error(client, body):
    response = client.post("/events/_doc", content=body)
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid JSON body"


def test_empty_body_and_cat_header_parsing(client):
    assert client.post("/events/_doc").status_code == 200
    assert rest_bridge._parse_cat_headers(" index, , count ") == ["index", "count"]


@pytest.mark.parametrize("body", [[], "text", 5])
def test_non_object_json_is_rejected(client, body):
    assert client.post("/events/_doc", json=body).status_code == 400
