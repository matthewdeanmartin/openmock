import pytest
from openmock.fake_server import (
    _coerce_bool,
    _get_field,
    _set_field,
    _delete_field,
    _merge_patch,
    FakeOpenSearchServer,
)


def test_coerce_bool():
    assert _coerce_bool(True) is True
    assert _coerce_bool("true") is True
    assert _coerce_bool("1") is True
    assert _coerce_bool("yes") is True
    assert _coerce_bool("on") is True
    assert _coerce_bool(False) is False
    assert _coerce_bool("false") is False
    assert _coerce_bool("0") is False
    assert _coerce_bool("no") is False
    assert _coerce_bool("off") is False
    assert _coerce_bool(None) is False


def test_field_utils():
    doc = {"a": {"b": {"c": 1}}}
    assert _get_field(doc, "a.b.c") == 1
    assert _get_field(doc, "a.b") == {"c": 1}
    with pytest.raises(KeyError):
        _get_field(doc, "a.x")
    assert _get_field(doc, "a.x", default=None) is None

    _set_field(doc, "a.d", 2)
    assert doc["a"]["d"] == 2
    _set_field(doc, "x.y.z", 3)
    assert doc["x"]["y"]["z"] == 3

    assert _delete_field(doc, "a.b.c") is True
    assert "c" not in doc["a"]["b"]
    assert _delete_field(doc, "a.x") is False


def test_merge_patch():
    existing = {"a": 1, "b": {"c": 2}}
    patch = {"b": {"d": 3}, "e": 4}
    merged = _merge_patch(existing, patch)
    assert merged == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}


def test_server_basics():
    server = FakeOpenSearchServer()
    assert server.info()["version"]["number"] is not None
    assert server.health()["status"] in ["green", "yellow", "red"]

    server.put_user("user1", {"pass": "123"})
    server.reset()
    assert server.get_user("user1") is None


def test_cat_count():
    server = FakeOpenSearchServer()
    server.index_document("idx", {"f": "v"})
    res = server.cat_count(format_type="json")
    assert res[0]["count"] == "1"


def test_processors_extra():
    server = FakeOpenSearchServer()
    server.put_pipeline(
        "p",
        {
            "processors": [
                {"uppercase": {"field": "u"}},
                {"remove": {"field": "r"}},
                {"append": {"field": "a", "value": ["v2"]}},
                {"split": {"field": "s", "separator": ","}},
                {"gsub": {"field": "g", "pattern": "a", "replacement": "b"}},
                {"json": {"field": "j", "target_field": "jo"}},
            ]
        },
    )

    doc = {
        "u": "hello",
        "r": "bye",
        "a": ["v1"],
        "s": "1,2,3",
        "g": "banana",
        "j": '{"key": "val"}',
    }

    processed = server.simulate_pipeline(
        body={"docs": [{"_source": doc}]}, pipeline_id="p"
    )["docs"][0]["doc"]["_source"]

    assert processed["u"] == "HELLO"
    assert "r" not in processed
    assert processed["a"] == ["v1", "v2"]
    assert processed["s"] == ["1", "2", "3"]
    assert processed["g"] == "bbnbnb"
    assert processed["jo"] == {"key": "val"}


def test_processor_errors():
    server = FakeOpenSearchServer()
    # Test ignore_failure
    server.put_pipeline(
        "p1",
        {"processors": [{"lowercase": {"field": "missing"}, "ignore_failure": True}]},
    )
    doc = {"f": "v"}
    processed = server.simulate_pipeline(
        body={"docs": [{"_source": doc}]}, pipeline_id="p1"
    )["docs"][0]["doc"]["_source"]
    assert processed == doc

    # Test on_failure
    server.put_pipeline(
        "p2",
        {
            "processors": [
                {
                    "lowercase": {"field": "missing"},
                    "on_failure": [{"set": {"field": "error", "value": True}}],
                }
            ]
        },
    )
    processed = server.simulate_pipeline(
        body={"docs": [{"_source": doc}]}, pipeline_id="p2"
    )["docs"][0]["doc"]["_source"]
    assert processed["error"] is True


def test_delete_resources():
    server = FakeOpenSearchServer()
    server.put_user("u", {})
    assert server.delete_user("u")["result"] == "deleted"
    assert server.delete_user("missing") is None

    server.put_role("r", {})
    assert server.delete_role("r")["result"] == "deleted"
    assert server.delete_role("missing") is None

    server.put_pipeline("p", {})
    assert server.delete_pipeline("p")["result"] == "deleted"
    assert server.delete_pipeline("missing") is None


def test_list_get_patch():
    server = FakeOpenSearchServer()
    # Users
    server.put_user("u1", {"a": 1})
    assert "u1" in server.list_users()
    assert server.get_user("u1")["u1"]["a"] == 1
    assert server.get_user("missing") is None
    server.patch_user("u1", {"b": 2})
    assert server.get_user("u1")["u1"]["b"] == 2
    assert server.patch_user("missing", {}) is None

    # Roles
    server.put_role("r1", {"a": 1})
    assert "r1" in server.list_roles()
    assert server.get_role("r1")["r1"]["a"] == 1
    assert server.get_role("missing") is None
    server.patch_role("r1", {"b": 2})
    assert server.get_role("r1")["r1"]["b"] == 2
    assert server.patch_role("missing", {}) is None

    # Pipelines
    server.put_pipeline("p1", {"description": "d1"})
    assert "p1" in server.list_pipelines()
    assert server.get_pipeline("p1")["p1"]["description"] == "d1"
    assert server.get_pipeline("missing") is None
    assert "p1" in server.get_pipeline()  # list all


def test_convert_processor():
    server = FakeOpenSearchServer()
    server.put_pipeline(
        "p",
        {
            "processors": [
                {"convert": {"field": "f1", "type": "integer"}},
                {"convert": {"field": "f2", "type": "float"}},
                {"convert": {"field": "f3", "type": "string"}},
                {"convert": {"field": "f4", "type": "boolean"}},
            ]
        },
    )
    doc = {"f1": "123", "f2": "1.5", "f3": 456, "f4": "on"}
    res = server.simulate_pipeline(body={"docs": [{"_source": doc}]}, pipeline_id="p")
    processed = res["docs"][0]["doc"]["_source"]
    assert processed["f1"] == 123
    assert processed["f2"] == 1.5
    assert processed["f3"] == "456"
    assert processed["f4"] is True


def test_cat_text():
    server = FakeOpenSearchServer()
    server.index_document("idx1", {"f": "v"})
    res = server.cat_indices(format_type="text", verbose=True)
    assert isinstance(res, str)
    assert "health" in res
    assert "idx1" in res


def test_extra_server_methods():
    server = FakeOpenSearchServer()
    server.create_document("idx", {"f": "v"}, "id1")
    assert server.count_documents("idx")["count"] == 1

    # Test _delete_field edge cases
    doc = {"a": 1}
    assert _delete_field(doc, "") is False
    assert _delete_field(doc, "b") is False
    assert _delete_field(doc, "a.b") is False
