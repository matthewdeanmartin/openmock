"""
Module initialization
"""

from asyncio import iscoroutinefunction
from functools import wraps
from unittest.mock import patch

from openmock.behaviour.server_failure import server_failure
from openmock.fake_asyncopensearch import AsyncFakeOpenSearch
from openmock.fake_cluster import FakeClusterClient
from openmock.fake_indices import FakeIndicesClient
from openmock.fake_opensearch import FakeOpenSearch
from openmock.normalize_hosts import _normalize_hosts

__all__ = [
    "openmock",
    "server_failure",
    "FakeOpenSearch",
    "AsyncFakeOpenSearch",
    "FakeClusterClient",
    "FakeIndicesClient",
]

OPEN_INSTANCES = {}


def _get_openmock(*args, hosts=None, **kwargs):
    host = _normalize_hosts(hosts)[0]
    open_key = f'{host.get("host", "localhost")}:{host.get("port", 9200)}'

    if open_key in OPEN_INSTANCES:
        connection = OPEN_INSTANCES.get(open_key)
    else:
        connection = FakeOpenSearch()
        OPEN_INSTANCES[open_key] = connection
    return connection


def openmock(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        OPEN_INSTANCES.clear()
        with patch("opensearchpy.OpenSearch", _get_openmock):
            return f(*args, **kwargs)

    @wraps(f)
    async def async_wrapper(*args, **kwargs):
        OPEN_INSTANCES.clear()
        with patch("opensearchpy.OpenSearch", _get_openmock):
            return await f(*args, **kwargs)

    return async_wrapper if iscoroutinefunction(f) else wrapper
