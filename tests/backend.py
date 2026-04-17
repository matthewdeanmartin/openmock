import asyncio
import inspect
import json
import os
from functools import wraps
from typing import Any
from unittest import skipIf
from unittest.mock import patch
from urllib.parse import urlparse

import opensearchpy
from opensearchpy.exceptions import NotFoundError

from openmock import openmock as openmock_decorator

TEST_BACKEND_ENV = "OPENMOCK_TEST_BACKEND"
REAL_OPENSEARCH_URL_ENV = "OPENMOCK_REAL_OPENSEARCH_URL"
DEFAULT_REAL_OPENSEARCH_URL = "http://localhost:9200"

_REAL_OPENSEARCH_CLASS = opensearchpy.OpenSearch
_REAL_ASYNC_OPENSEARCH_CLASS = opensearchpy.AsyncOpenSearch


def using_real_opensearch() -> bool:
    return os.getenv(TEST_BACKEND_ENV, "mock").strip().lower() == "real"


def mock_only(reason: str):
    return skipIf(using_real_opensearch(), reason)


def get_test_hosts() -> list[dict[str, Any]]:
    raw_url = os.getenv(REAL_OPENSEARCH_URL_ENV, DEFAULT_REAL_OPENSEARCH_URL)
    parsed = urlparse(raw_url)
    scheme = parsed.scheme or "http"
    port = parsed.port or (443 if scheme == "https" else 9200)
    return [{"host": parsed.hostname or "localhost", "port": port, "scheme": scheme}]


def _client_kwargs(hosts=None, **kwargs):
    options = dict(kwargs)
    resolved_hosts = hosts or options.pop("hosts", None) or get_test_hosts()
    options["hosts"] = resolved_hosts
    scheme = resolved_hosts[0].get("scheme", "http")
    if scheme == "https":
        options.setdefault("use_ssl", True)
        options.setdefault("verify_certs", False)
        options.setdefault("ssl_assert_hostname", False)
        options.setdefault("ssl_show_warn", False)
    return options


def _with_refresh(params):
    merged = dict(params or {})
    merged.setdefault("refresh", "wait_for")
    return merged


def _normalize_bulk_body(body):
    if not isinstance(body, str):
        return body

    normalized_lines = []
    expects_source = False
    last_action = None

    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        line = json.loads(raw_line)
        if not expects_source:
            action_name, action_data = next(iter(line.items()))
            if isinstance(action_data, dict):
                action_data.pop("_type", None)
            normalized_lines.append(json.dumps(line, default=str))
            expects_source = action_name != "delete"
            last_action = action_name
            continue

        if last_action == "update" and "doc" not in line and "script" not in line:
            line = {"doc": line}
        normalized_lines.append(json.dumps(line, default=str))
        expects_source = False
        last_action = None

    return "\n".join(normalized_lines)


def _bulk_action_defaults(body):
    if not isinstance(body, str):
        return []

    defaults = []
    expects_source = False
    for raw_line in body.splitlines():
        if not raw_line.strip():
            continue
        line = json.loads(raw_line)
        if expects_source:
            expects_source = False
            continue

        action_name, action_data = next(iter(line.items()))
        doc_type = "_doc"
        if isinstance(action_data, dict):
            doc_type = action_data.get("_type", "_doc")
        defaults.append((action_name, doc_type))
        expects_source = action_name != "delete"

    return defaults


def _normalize_bulk_response(data, action_defaults):
    items = data.get("items", [])
    for item, (expected_action, expected_doc_type) in zip(items, action_defaults):
        payload = item.get(expected_action)
        if not isinstance(payload, dict):
            continue
        payload.setdefault("_type", expected_doc_type)
        error = payload.get("error")
        if isinstance(error, dict) and "type" in error:
            payload["error"] = error["type"]
    return data


class LiveOpenSearchAdapter:
    def __init__(self, client):
        self._client = client
        self.indices = LiveIndicesAdapter(client.indices)
        self.cluster = client.cluster

    def create(
        self,
        index: Any,
        id: Any,
        body: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.create(
            index=index,
            id=id,
            body=body,
            params=_with_refresh(params),
            headers=headers,
        )

    def index(
        self,
        index: Any,
        body: Any,
        id: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
        **kwargs,
    ) -> Any:
        del doc_type
        return self._client.index(
            index=index,
            body=body,
            id=id,
            params=_with_refresh(params),
            headers=headers,
            **kwargs,
        )

    def exists(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.exists(index=index, id=id, params=params, headers=headers)

    def get(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.get(index=index, id=id, params=params, headers=headers)

    def search(
        self,
        index: Any = None,
        body: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.search(
            index=index, body=body, params=params, headers=headers
        )

    def count(
        self,
        index: Any = None,
        body: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.count(index=index, body=body, params=params, headers=headers)

    def delete(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return self._client.delete(
            index=index, id=id, params=_with_refresh(params), headers=headers
        )

    def bulk(self, body: Any, index: Any = None, params: Any = None, headers: Any = None):
        action_defaults = _bulk_action_defaults(body)
        response = self._client.bulk(
            body=_normalize_bulk_body(body),
            index=index,
            params=_with_refresh(params),
            headers=headers,
        )
        return _normalize_bulk_response(response, action_defaults)

    def update(self, *args, params: Any = None, **kwargs):
        return self._client.update(*args, params=_with_refresh(params), **kwargs)

    def update_by_query(self, *args, params: Any = None, **kwargs):
        return self._client.update_by_query(
            *args, params=_with_refresh(params), **kwargs
        )

    def __getattr__(self, item):
        return getattr(self._client, item)


class AsyncLiveOpenSearchAdapter:
    def __init__(self, client):
        self._client = client
        self.indices = AsyncLiveIndicesAdapter(client.indices)
        self.cluster = client.cluster

    async def create(
        self,
        index: Any,
        id: Any,
        body: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.create(
            index=index,
            id=id,
            body=body,
            params=_with_refresh(params),
            headers=headers,
        )

    async def index(
        self,
        index: Any,
        body: Any,
        id: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
        **kwargs,
    ) -> Any:
        del doc_type
        return await self._client.index(
            index=index,
            body=body,
            id=id,
            params=_with_refresh(params),
            headers=headers,
            **kwargs,
        )

    async def exists(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.exists(
            index=index, id=id, params=params, headers=headers
        )

    async def get(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.get(index=index, id=id, params=params, headers=headers)

    async def search(
        self,
        index: Any = None,
        body: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.search(
            index=index, body=body, params=params, headers=headers
        )

    async def count(
        self,
        index: Any = None,
        body: Any = None,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.count(
            index=index, body=body, params=params, headers=headers
        )

    async def delete(
        self,
        index: Any,
        id: Any,
        doc_type: Any = None,
        params: Any = None,
        headers: Any = None,
    ) -> Any:
        del doc_type
        return await self._client.delete(
            index=index, id=id, params=_with_refresh(params), headers=headers
        )

    async def bulk(
        self, body: Any, index: Any = None, params: Any = None, headers: Any = None
    ):
        action_defaults = _bulk_action_defaults(body)
        response = await self._client.bulk(
            body=_normalize_bulk_body(body),
            index=index,
            params=_with_refresh(params),
            headers=headers,
        )
        return _normalize_bulk_response(response, action_defaults)

    async def update(self, *args, params: Any = None, **kwargs):
        return await self._client.update(*args, params=_with_refresh(params), **kwargs)

    async def update_by_query(self, *args, params: Any = None, **kwargs):
        return await self._client.update_by_query(
            *args, params=_with_refresh(params), **kwargs
        )

    def __getattr__(self, item):
        return getattr(self._client, item)


def _get_real_opensearch(*args, hosts=None, **kwargs):
    del args
    return LiveOpenSearchAdapter(_REAL_OPENSEARCH_CLASS(**_client_kwargs(hosts, **kwargs)))


def _get_async_real_opensearch(*args, hosts=None, **kwargs):
    del args
    return AsyncLiveOpenSearchAdapter(
        _REAL_ASYNC_OPENSEARCH_CLASS(**_client_kwargs(hosts, **kwargs))
    )


class LiveIndicesAdapter:
    def __init__(self, client):
        self._client = client

    def create(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return self._client.create(
            index=index, params=params, headers=headers, **kwargs
        )

    def exists(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return self._client.exists(
            index=index, params=params, headers=headers, **kwargs
        )

    def delete(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        delete_params = dict(params or {})
        delete_params.setdefault("ignore_unavailable", "true")
        return self._client.delete(
            index=index, params=delete_params, headers=headers, **kwargs
        )

    def refresh(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return self._client.refresh(
            index=index, params=params, headers=headers, **kwargs
        )

    def get(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return self._client.get(index=index, params=params, headers=headers, **kwargs)

    def __getattr__(self, item):
        return getattr(self._client, item)


class AsyncLiveIndicesAdapter:
    def __init__(self, client):
        self._client = client

    async def create(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return await self._client.create(
            index=index, params=params, headers=headers, **kwargs
        )

    async def exists(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return await self._client.exists(
            index=index, params=params, headers=headers, **kwargs
        )

    async def delete(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        delete_params = dict(params or {})
        delete_params.setdefault("ignore_unavailable", "true")
        return await self._client.delete(
            index=index, params=delete_params, headers=headers, **kwargs
        )

    async def refresh(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return await self._client.refresh(
            index=index, params=params, headers=headers, **kwargs
        )

    async def get(self, index: Any, params: Any = None, headers: Any = None, **kwargs):
        return await self._client.get(
            index=index, params=params, headers=headers, **kwargs
        )

    def __getattr__(self, item):
        return getattr(self._client, item)


def cleanup_sync_client(client) -> None:
    if not using_real_opensearch():
        return

    raw_client = getattr(client, "_client", client)
    try:
        indices = raw_client.indices.get(index="*")
    except NotFoundError:
        return

    user_indices = [name for name in indices if not name.startswith(".")]
    if user_indices:
        raw_client.indices.delete(
            index=",".join(user_indices),
            ignore=[400, 404],
            params={"expand_wildcards": "all"},
        )
        # Wait for cluster to acknowledge so subsequent tests see a clean state.
        try:
            raw_client.cluster.health(params={"wait_for_status": "yellow", "timeout": "5s"})
        except Exception:
            pass


async def cleanup_async_client(client) -> None:
    if not using_real_opensearch():
        return

    raw_client = getattr(client, "_client", client)
    try:
        indices = await raw_client.indices.get(index="*")
    except NotFoundError:
        return

    user_indices = [name for name in indices if not name.startswith(".")]
    if user_indices:
        await raw_client.indices.delete(
            index=",".join(user_indices),
            ignore=[400, 404],
            params={"expand_wildcards": "all"},
        )
        try:
            await raw_client.cluster.health(
                params={"wait_for_status": "yellow", "timeout": "5s"}
            )
        except Exception:
            pass


def cleanup_real_cluster() -> None:
    if not using_real_opensearch():
        return
    client = _get_real_opensearch()
    try:
        cleanup_sync_client(client)
    finally:
        raw_client = getattr(client, "_client", client)
        close = getattr(raw_client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


async def cleanup_real_cluster_async() -> None:
    if not using_real_opensearch():
        return
    client = _get_async_real_opensearch()
    try:
        await cleanup_async_client(client)
    finally:
        raw_client = getattr(client, "_client", client)
        close = getattr(raw_client, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:
                pass


async def _close_async_client(client) -> None:
    raw_client = getattr(client, "_client", client)
    close = getattr(raw_client, "close", None)
    if callable(close):
        try:
            await close()
        except Exception:
            pass


def _close_sync_client(client) -> None:
    raw_client = getattr(client, "_client", client)
    close = getattr(raw_client, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def openmock(f):
    if not using_real_opensearch():
        return openmock_decorator(f)

    @wraps(f)
    def wrapper(*args, **kwargs):
        cleanup_real_cluster()
        with (
            patch("opensearchpy.OpenSearch", _get_real_opensearch),
            patch("opensearchpy.AsyncOpenSearch", _get_async_real_opensearch),
        ):
            return f(*args, **kwargs)

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        await cleanup_real_cluster_async()
        with (
            patch("opensearchpy.OpenSearch", _get_real_opensearch),
            patch("opensearchpy.AsyncOpenSearch", _get_async_real_opensearch),
        ):
            return await f(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(f) else wrapper


def close_test_client_sync(client) -> None:
    _close_sync_client(client)


async def close_test_client_async(client) -> None:
    await _close_async_client(client)
