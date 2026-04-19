"""
Module initialization
"""

import inspect
from functools import wraps
from unittest.mock import patch

from opensearchpy.exceptions import ConnectionError

from openmock.behaviour.server_failure import server_failure
from openmock.fake_asyncindices import FakeAsyncIndicesClient
from openmock.fake_asyncopensearch import AsyncFakeOpenSearch
from openmock.fake_cluster import FakeClusterClient
from openmock.fake_indices import FakeIndicesClient
from openmock.fake_opensearch import FakeOpenSearch
from openmock.fake_server import FakeOpenSearchServer
from openmock.normalize_hosts import _normalize_hosts

__all__ = [
    "openmock",
    "server_failure",
    "FakeOpenSearch",
    "FakeOpenSearchServer",
    "AsyncFakeOpenSearch",
    "FakeClusterClient",
    "FakeIndicesClient",
]

OPEN_INSTANCES = {}
OPEN_ASYNC_INSTANCES = {}


def _get_openmock(*args, hosts=None, **kwargs):
    host = _normalize_hosts(hosts)[0]
    open_key = f'{host.get("host", "localhost")}:{host.get("port", 9200)}'

    if open_key in OPEN_INSTANCES:
        connection = OPEN_INSTANCES.get(open_key)
    else:
        connection = FakeOpenSearch()
        OPEN_INSTANCES[open_key] = connection
    return connection


def _get_async_openmock(*args, hosts=None, **kwargs):
    host = _normalize_hosts(hosts)[0]
    open_key = f'{host.get("host", "localhost")}:{host.get("port", 9200)}'

    if open_key in OPEN_ASYNC_INSTANCES:
        connection = OPEN_ASYNC_INSTANCES.get(open_key)
    else:
        connection = AsyncFakeOpenSearch()
        OPEN_ASYNC_INSTANCES[open_key] = connection
    return connection


def _fail_on_real_connection(*args, **kwargs):
    raise ConnectionError(
        "N/A", "Attempted to connect to real OpenSearch server during openmock.", "N/A"
    )


def openmock(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        OPEN_INSTANCES.clear()
        OPEN_ASYNC_INSTANCES.clear()
        with (
            patch("opensearchpy.OpenSearch", _get_openmock),
            patch("opensearchpy.AsyncOpenSearch", _get_async_openmock),
            patch("opensearchpy.client.indices.IndicesClient", FakeIndicesClient),
            patch("opensearchpy.client.cluster.ClusterClient", FakeClusterClient),
            patch(
                "opensearchpy._async.client.indices.IndicesClient",
                FakeAsyncIndicesClient,
            ),
            patch(
                "opensearchpy._async.client.cluster.ClusterClient", FakeClusterClient
            ),
            patch(
                "opensearchpy.transport.Transport.perform_request",
                _fail_on_real_connection,
            ),
            patch(
                "opensearchpy._async.transport.AsyncTransport.perform_request",
                _fail_on_real_connection,
            ),
        ):
            return f(*args, **kwargs)

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        OPEN_INSTANCES.clear()
        OPEN_ASYNC_INSTANCES.clear()
        with (
            patch("opensearchpy.OpenSearch", _get_openmock),
            patch("opensearchpy.AsyncOpenSearch", _get_async_openmock),
            patch("opensearchpy.client.indices.IndicesClient", FakeIndicesClient),
            patch("opensearchpy.client.cluster.ClusterClient", FakeClusterClient),
            patch(
                "opensearchpy._async.client.indices.IndicesClient",
                FakeAsyncIndicesClient,
            ),
            patch(
                "opensearchpy._async.client.cluster.ClusterClient", FakeClusterClient
            ),
            patch(
                "opensearchpy.transport.Transport.perform_request",
                _fail_on_real_connection,
            ),
            patch(
                "opensearchpy._async.transport.AsyncTransport.perform_request",
                _fail_on_real_connection,
            ),
        ):
            return await f(*args, **kwargs)

    return async_wrapper if inspect.iscoroutinefunction(f) else wrapper
