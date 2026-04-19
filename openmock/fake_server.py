"""Shared fake server features for the web UI and REST bridge."""

from __future__ import annotations

import copy
import datetime as dt
import json
import re
import time
from typing import Any

from openmock.behaviour.server_failure import server_failure
from openmock.fake_opensearch import FakeOpenSearch
from openmock.utilities.decorator import for_all_methods

_PROCESSOR_META_KEYS = {"description", "if", "ignore_failure", "on_failure", "tag"}
_MISSING = object()


def _deepcopy(value: Any) -> Any:
    return copy.deepcopy(value)


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return bool(value)


def _field_parts(field: str) -> list[str]:
    return [part for part in str(field).split(".") if part]


def _get_field(document: dict[str, Any], field: str, default: Any = _MISSING) -> Any:
    current: Any = document
    for part in _field_parts(field):
        if not isinstance(current, dict) or part not in current:
            if default is _MISSING:
                raise KeyError(field)
            return default
        current = current[part]
    return current


def _set_field(document: dict[str, Any], field: str, value: Any) -> None:
    parts = _field_parts(field)
    if not parts:
        raise ValueError("field is required")

    current = document
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    current[parts[-1]] = value


def _delete_field(document: dict[str, Any], field: str) -> bool:
    parts = _field_parts(field)
    if not parts:
        return False

    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    if not isinstance(current, dict) or parts[-1] not in current:
        return False
    del current[parts[-1]]
    return True


def _merge_patch(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = _deepcopy(existing)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_patch(merged[key], value)
        else:
            merged[key] = _deepcopy(value)
    return merged


@for_all_methods([server_failure])
class FakeOpenSearchServer:
    """Development-only fake server state used by the UI and HTTP bridge."""

    def __init__(self, es: FakeOpenSearch | None = None) -> None:
        self.es = es or FakeOpenSearch()
        self._users: dict[str, dict[str, Any]] = {}
        self._roles: dict[str, dict[str, Any]] = {}
        self._pipelines: dict[str, dict[str, Any]] = {}

    def reset(self) -> None:
        self.es = FakeOpenSearch()
        self._users = {}
        self._roles = {}
        self._pipelines = {}

    def info(self) -> dict[str, Any]:
        return self.es.info()

    def health(self) -> dict[str, Any]:
        return self.es.cluster.health()

    def list_users(self) -> dict[str, dict[str, Any]]:
        return _deepcopy(self._users)

    def get_user(self, username: str) -> dict[str, dict[str, Any]] | None:
        if username not in self._users:
            return None
        return {username: _deepcopy(self._users[username])}

    def put_user(
        self, username: str, body: dict[str, Any] | None = None
    ) -> dict[str, str]:
        existed = username in self._users
        payload = _deepcopy(body or {})
        payload.setdefault("attributes", {})
        payload.setdefault("backend_roles", [])
        payload.setdefault("opendistro_security_roles", [])
        payload.setdefault("reserved", False)
        payload.setdefault("hidden", False)
        self._users[username] = payload
        return {
            "status": "OK",
            "result": "updated" if existed else "created",
            "message": f"User '{username}' {'updated' if existed else 'created'}.",
        }

    def patch_user(
        self, username: str, body: dict[str, Any] | None = None
    ) -> dict[str, str] | None:
        if username not in self._users:
            return None
        self._users[username] = _merge_patch(self._users[username], body or {})
        return {
            "status": "OK",
            "result": "updated",
            "message": f"User '{username}' updated.",
        }

    def delete_user(self, username: str) -> dict[str, str] | None:
        if username not in self._users:
            return None
        del self._users[username]
        return {
            "status": "OK",
            "result": "deleted",
            "message": f"User '{username}' deleted.",
        }

    def list_roles(self) -> dict[str, dict[str, Any]]:
        return _deepcopy(self._roles)

    def get_role(self, role_name: str) -> dict[str, dict[str, Any]] | None:
        if role_name not in self._roles:
            return None
        return {role_name: _deepcopy(self._roles[role_name])}

    def put_role(
        self, role_name: str, body: dict[str, Any] | None = None
    ) -> dict[str, str]:
        existed = role_name in self._roles
        payload = _deepcopy(body or {})
        payload.setdefault("cluster_permissions", [])
        payload.setdefault("index_permissions", [])
        payload.setdefault("tenant_permissions", [])
        self._roles[role_name] = payload
        return {
            "status": "OK",
            "result": "updated" if existed else "created",
            "message": f"Role '{role_name}' {'updated' if existed else 'created'}.",
        }

    def patch_role(
        self, role_name: str, body: dict[str, Any] | None = None
    ) -> dict[str, str] | None:
        if role_name not in self._roles:
            return None
        self._roles[role_name] = _merge_patch(self._roles[role_name], body or {})
        return {
            "status": "OK",
            "result": "updated",
            "message": f"Role '{role_name}' updated.",
        }

    def delete_role(self, role_name: str) -> dict[str, str] | None:
        if role_name not in self._roles:
            return None
        del self._roles[role_name]
        return {
            "status": "OK",
            "result": "deleted",
            "message": f"Role '{role_name}' deleted.",
        }

    def list_pipelines(self) -> dict[str, dict[str, Any]]:
        return _deepcopy(self._pipelines)

    def get_pipeline(self, pipeline_id: str | None = None) -> dict[str, Any] | None:
        if pipeline_id is None:
            return self.list_pipelines()
        if pipeline_id not in self._pipelines:
            return None
        return {pipeline_id: _deepcopy(self._pipelines[pipeline_id])}

    def put_pipeline(
        self, pipeline_id: str, body: dict[str, Any] | None = None
    ) -> dict[str, str]:
        existed = pipeline_id in self._pipelines
        payload = _deepcopy(body or {})
        payload.setdefault("description", "")
        payload.setdefault("processors", [])
        payload.setdefault("on_failure", [])
        self._pipelines[pipeline_id] = payload
        return {
            "status": "OK",
            "result": "updated" if existed else "created",
            "message": f"Pipeline '{pipeline_id}' {'updated' if existed else 'created'}.",
        }

    def delete_pipeline(self, pipeline_id: str) -> dict[str, str] | None:
        if pipeline_id not in self._pipelines:
            return None
        del self._pipelines[pipeline_id]
        return {
            "status": "OK",
            "result": "deleted",
            "message": f"Pipeline '{pipeline_id}' deleted.",
        }

    def simulate_pipeline(
        self, body: dict[str, Any] | None = None, pipeline_id: str | None = None
    ) -> dict[str, Any]:
        payload = _deepcopy(body or {})
        pipeline_definition = payload.get("pipeline")
        if pipeline_definition is None:
            if pipeline_id is None or pipeline_id not in self._pipelines:
                raise KeyError(f"Unknown pipeline '{pipeline_id}'.")
            pipeline_definition = self._pipelines[pipeline_id]

        docs = payload.get("docs", [])
        results = []
        for item in docs:
            source = _deepcopy(item.get("_source"))
            if source is None:
                source = _deepcopy(item.get("doc", {}).get("_source", {}))
            processed = self._run_pipeline_definition(pipeline_definition, source)
            results.append(
                {
                    "doc": {
                        "_source": processed,
                        "_ingest": {"pipeline": pipeline_id or "_inline"},
                    }
                }
            )
        return {"docs": results}

    def index_document(
        self,
        index: str,
        body: dict[str, Any],
        document_id: str | None = None,
        pipeline: str | None = None,
    ) -> dict[str, Any]:
        payload = self._apply_pipeline(body, pipeline)
        return self.es.index(index=index, body=payload, id=document_id)

    def create_document(
        self,
        index: str,
        body: dict[str, Any],
        document_id: str,
        pipeline: str | None = None,
    ) -> dict[str, Any]:
        payload = self._apply_pipeline(body, pipeline)
        return self.es.create(index=index, id=document_id, body=payload)

    def search_documents(
        self, index: str | list[str] | None = None, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.es.search(index=index, body=body)

    def count_documents(
        self, index: str | list[str] | None = None, body: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return self.es.count(index=index, body=body)

    def cat_indices(
        self,
        format_type: str = "text",
        verbose: bool = False,
        headers: list[str] | None = None,
    ) -> str | list[dict[str, str]]:
        rows = []
        documents = self.es._FakeIndicesClient__documents_dict
        for index_name, docs in sorted(documents.items()):
            rows.append(
                {
                    "health": "green",
                    "status": "open",
                    "index": index_name,
                    "docs.count": str(len(docs)),
                    "docs.deleted": "0",
                }
            )
        selected_headers = headers or [
            "health",
            "status",
            "index",
            "docs.count",
            "docs.deleted",
        ]
        return self._format_cat(rows, selected_headers, format_type, verbose)

    def cat_count(
        self,
        format_type: str = "text",
        verbose: bool = False,
        headers: list[str] | None = None,
        index: str | None = None,
        body: dict[str, Any] | None = None,
    ) -> str | list[dict[str, str]]:
        count = self.count_documents(index=index, body=body).get("count", 0)
        now = dt.datetime.utcnow()
        rows = [
            {
                "epoch": str(int(time.time())),
                "timestamp": now.strftime("%H:%M:%S"),
                "count": str(count),
            }
        ]
        selected_headers = headers or ["epoch", "timestamp", "count"]
        return self._format_cat(rows, selected_headers, format_type, verbose)

    def _apply_pipeline(
        self, body: dict[str, Any], pipeline: str | None = None
    ) -> dict[str, Any]:
        payload = _deepcopy(body)
        if pipeline is None:
            return payload
        if pipeline not in self._pipelines:
            raise KeyError(f"Unknown pipeline '{pipeline}'.")
        return self._run_pipeline_definition(self._pipelines[pipeline], payload)

    def _run_pipeline_definition(
        self, pipeline_definition: dict[str, Any], source: dict[str, Any]
    ) -> dict[str, Any]:
        document = _deepcopy(source)
        pipeline_on_failure = pipeline_definition.get("on_failure", [])
        for processor in pipeline_definition.get("processors", []):
            self._apply_processor(processor, document, pipeline_on_failure)
        return document

    def _apply_processor(
        self,
        processor: dict[str, Any],
        document: dict[str, Any],
        pipeline_on_failure: list[dict[str, Any]],
    ) -> None:
        processor_name = next(
            (key for key in processor if key not in _PROCESSOR_META_KEYS),
            None,
        )
        if processor_name is None:
            raise ValueError("Processor definition is missing a processor name.")

        config = processor.get(processor_name, {}) or {}
        ignore_failure = bool(processor.get("ignore_failure", False))
        on_failure = processor.get("on_failure", [])

        try:
            self._run_named_processor(processor_name, config, document)
        except (KeyError, TypeError, ValueError) as exc:
            failure_chain = on_failure or pipeline_on_failure
            if failure_chain:
                for failure_processor in failure_chain:
                    self._apply_processor(failure_processor, document, [])
                return
            if ignore_failure:
                return
            raise exc

    def _run_named_processor(
        self, processor_name: str, config: dict[str, Any], document: dict[str, Any]
    ) -> None:
        if processor_name == "set":
            field = config["field"]
            override = config.get("override", True)
            if not override and _get_field(document, field, _MISSING) is not _MISSING:
                return
            _set_field(document, field, _deepcopy(config.get("value")))
            return

        if processor_name == "rename":
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            _set_field(document, config["target_field"], value)
            _delete_field(document, field)
            return

        if processor_name == "remove":
            fields = config["field"]
            if isinstance(fields, str):
                fields = [fields]
            ignore_missing = config.get("ignore_missing", False)
            for field in fields:
                removed = _delete_field(document, field)
                if not removed and not ignore_missing:
                    raise KeyError(field)
            return

        if processor_name == "append":
            field = config["field"]
            current = _get_field(document, field, _MISSING)
            values = config.get("value", [])
            if not isinstance(values, list):
                values = [values]
            if current is _MISSING:
                _set_field(document, field, _deepcopy(values))
                return
            if isinstance(current, list):
                current.extend(_deepcopy(values))
                return
            _set_field(document, field, [current, *_deepcopy(values)])
            return

        if processor_name in {"lowercase", "uppercase", "trim"}:
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            if not isinstance(value, str):
                raise TypeError(f"Field '{field}' must be a string.")
            if processor_name == "lowercase":
                _set_field(document, field, value.lower())
            elif processor_name == "uppercase":
                _set_field(document, field, value.upper())
            else:
                _set_field(document, field, value.strip())
            return

        if processor_name == "split":
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            if not isinstance(value, str):
                raise TypeError(f"Field '{field}' must be a string.")
            target_field = config.get("target_field", field)
            _set_field(document, target_field, value.split(config["separator"]))
            return

        if processor_name == "convert":
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            target_type = config["type"]
            converted: Any
            if target_type in {"integer", "long"}:
                converted = int(value)
            elif target_type in {"float", "double"}:
                converted = float(value)
            elif target_type == "string":
                converted = str(value)
            elif target_type == "boolean":
                converted = _coerce_bool(value)
            else:
                raise ValueError(f"Unsupported convert type '{target_type}'.")
            _set_field(document, field, converted)
            return

        if processor_name == "gsub":
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            if not isinstance(value, str):
                raise TypeError(f"Field '{field}' must be a string.")
            _set_field(
                document,
                field,
                re.sub(config["pattern"], config["replacement"], value),
            )
            return

        if processor_name == "json":
            field = config["field"]
            value = _get_field(document, field, _MISSING)
            if value is _MISSING:
                if config.get("ignore_missing", False):
                    return
                raise KeyError(field)
            if not isinstance(value, str):
                raise TypeError(f"Field '{field}' must be a JSON string.")
            target_field = config.get("target_field", field)
            _set_field(document, target_field, json.loads(value))
            return

        raise ValueError(f"Unsupported processor '{processor_name}'.")

    def _format_cat(
        self,
        rows: list[dict[str, str]],
        headers: list[str],
        format_type: str,
        verbose: bool,
    ) -> str | list[dict[str, str]]:
        normalized_rows = [
            {header: str(row.get(header, "")) for header in headers} for row in rows
        ]
        if format_type.lower() == "json":
            return normalized_rows

        widths = {header: len(header) for header in headers}
        for row in normalized_rows:
            for header in headers:
                widths[header] = max(widths[header], len(row.get(header, "")))

        def _render_row(row: dict[str, str]) -> str:
            return " ".join(
                row.get(header, "").ljust(widths[header]) for header in headers
            ).rstrip()

        lines = []
        if verbose:
            lines.append(_render_row({header: header for header in headers}))
        lines.extend(_render_row(row) for row in normalized_rows)
        return "\n".join(lines)
