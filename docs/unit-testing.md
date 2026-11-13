# Using Openmock in unit tests

Openmock supports a **unit-test fake** style: your production code still talks to `opensearchpy.OpenSearch` or `opensearchpy.AsyncOpenSearch`, but tests replace those constructors with a stateful in-memory surrogate.

The result is more realistic than a stubbed return value and lighter than spinning up a real cluster for every test.

## What style of test this is

Openmock is a **test surrogate** that statefully mimics parts of OpenSearch:

- documents are stored in memory,
- repeated client calls see shared state,
- responses look like OpenSearch responses,
- queries run against that stored state.

This is useful when the unit under test spans several OpenSearch operations and you want the test to express business behavior instead of low-level call assertions.

## Basic pattern

Decorate the test method, or a `setUp()` that creates the client, with `@openmock`.

```python
from unittest import TestCase

import opensearchpy

from openmock import openmock


class SearchService:
    def __init__(self) -> None:
        self.client = opensearchpy.OpenSearch(
            hosts=[{"host": "localhost", "port": 9200}]
        )

    def create_article(self, article: dict) -> str:
        result = self.client.index(index="articles", body=article)
        return result["_id"]

    def get_article(self, article_id: str) -> dict:
        result = self.client.get(index="articles", id=article_id)
        return result["_source"]


class SearchServiceTests(TestCase):
    @openmock
    def test_round_trip(self) -> None:
        service = SearchService()

        article_id = service.create_article(
            {"title": "Openmock", "category": "docs"}
        )

        article = service.get_article(article_id)

        self.assertEqual(
            {"title": "Openmock", "category": "docs"},
            article,
        )
```

## Why this works well

The fake preserves state across calls within a test, so the test can read like a real workflow:

1. call application code,
1. let it write documents,
1. call application code again,
1. observe the effect of the earlier write.

That keeps tests focused on behavior instead of hand-maintained mock expectations.

## Constructor patching model

`@openmock` patches:

- `opensearchpy.OpenSearch`
- `opensearchpy.AsyncOpenSearch`

Inside the decorated scope, new client instances become `FakeOpenSearch` or `AsyncFakeOpenSearch`.

Two important implications:

1. Create clients **inside** the decorated test or decorated setup.
1. If your application creates a client at import time and caches it globally, that instance will not be replaced.

## Shared fake state inside one test

Openmock caches fake instances by normalized host and port. In practice that means:

- two clients of the same kind (sync or async) with the same host configuration share data,
- a different host or port gives you a separate fake instance,
- sync and async clients use separate stores,
- each decorated call clears the caches, so avoid nesting decorated helpers inside decorated tests.

This makes multi-object tests convenient:

```python
@openmock
def test_repository_and_service_share_state():
    repo_client = opensearchpy.OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}]
    )
    service_client = opensearchpy.OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}]
    )

    repo_client.index(index="orders", id="42", body={"status": "new"})
    document = service_client.get(index="orders", id="42")

    assert document["_source"]["status"] == "new"
```

## Supported testing workflows

The in-memory fake is meant for the common workflows already covered by the test suite, including:

- `index`, `create`, `get`, `exists`, `delete`,
- `update` and `update_by_query`,
- `count`, `search`, `scroll`, `msearch`,
- `mget` and `get_source`,
- synthetic `suggest` responses (not real suggestions),
- index management through `client.indices`,
- cluster health and info calls.

Search support includes practical query shapes such as:

- `match_all`,
- `match` and `term`,
- `terms`,
- `bool` with `filter`, `must`, `must_not`, and `should`,
- `multi_match`,
- `range`,
- `exists`,
- simple `terms` aggregation,
- `composite` aggregation,
- `cardinality` metric aggregation (inside `composite` only).

**Not supported** (unknown query types raise `NotImplementedError`; unsupported top-level aggregations may return empty buckets):

- `wildcard`, `prefix`, `fuzzy`, `regexp` queries,
- `nested` and `geo` queries,
- `script` queries and aggregations,
- numeric aggregations (`avg`, `sum`, `min`, `max`, `percentiles`),
- `date_histogram` and `histogram` aggregations,
- relevance scoring (`_score` is a constant 1.0, not a relevance calculation),
- full-text analyzers, stemming, and highlighting.

It is still a fake, not a full OpenSearch clone. When behavior details matter, the tests under `tests/fake_opensearch` and `tests/fake_asyncopensearch` are the best executable specification.

## Example: searching with aggregate results

```python
from unittest import TestCase

import opensearchpy

from openmock import openmock


class CatalogTests(TestCase):
    @openmock
    def test_terms_aggregation(self) -> None:
        es = opensearchpy.OpenSearch()
        es.index(index="products", body={"category": "books"})
        es.index(index="products", body={"category": "books"})
        es.index(index="products", body={"category": "games"})

        result = es.search(
            index="products",
            body={"aggs": {"categories": {"terms": {"field": "category"}}}},
        )

        buckets = result["aggregations"]["categories"]["buckets"]
        self.assertEqual("books", buckets[0]["key"])
        self.assertEqual(2, buckets[0]["doc_count"])
```

## Example: async code

```python
import opensearchpy

from openmock import openmock


@openmock
async def test_async_round_trip() -> None:
    es = opensearchpy.AsyncOpenSearch()

    created = await es.index(index="events", body={"kind": "signup"})
    loaded = await es.get(index="events", id=created["_id"])

    assert loaded["_source"]["kind"] == "signup"
```

## Simulating failures

The `server_failure` behavior forces decorated methods on the fake clients to return the same error-shaped payload:

```python
from openmock import behaviour
from openmock import openmock


@openmock
def test_handles_server_error():
    behaviour.server_failure.enable()
    try:
        result = my_function_that_talks_to_opensearch()
        assert result == {"status_code": 500, "error": "Internal Server Error"}
    finally:
        behaviour.disable_all()
```

Use this when your code needs to react to a backend outage without standing up a broken server.

## When to use Openmock vs a real backend

Use Openmock when you want:

- fast unit tests,
- deterministic state,
- easy setup,
- test scenarios that span several OpenSearch calls.

Use a real backend when you need:

- exact OpenSearch behavior,
- confidence in edge-case query semantics,
- coverage for API features the fake does not implement.

This repository keeps both paths: the normal test flow uses the in-memory fake, and the parity flow can route the same tests to a live OpenSearch instance.

## Common gotchas

- Instantiate the client inside the decorated scope.
- Remember that fake state is process-local and in-memory only.
- Prefer asserting on business outcomes, not the fake's private internals.
- If a test depends on subtle OpenSearch semantics, run it against the real backend too.

## Maintenance parity coverage

Verified on 2026-11-12 against **opensearch-py 3.2.0 / OpenSearch 3.9.0**:
45 selected parity tests pass on Python 3.15.0. The [compatibility table](compatibility.md)
records the full Python/client matrix and the exact local results.

`tests/test_maintenance_parity.py` runs the same assertions against raw real and
fake clients, in both sync and async modes. It checks default ten-hit pagination,
body/query parameter precedence, zero-sized pages, negative pagination errors,
multi-field scalar sorting, missing values last, scrolling with body page sizes,
count/update-by-query/delete-by-query beyond ten documents, and document copy
isolation. The other parity suites cover CRUD, bulk, basic queries, aliases,
metadata, and terms aggregations. This is contract coverage for that subset;
it is not a claim of complete OpenSearch compatibility.

Search now returns ten hits by default, just like OpenSearch. Tests that need more
must request a larger `size` or scroll. Sort support is limited to flat scalar
source fields; analyzer semantics, distributed execution, snapshot isolation for
scrolls, and sophisticated scripting remain outside the mock's scope.

The REST security endpoints are development-only in-memory helpers. PATCH uses
object merging, not the Security plugin's RFC 6902 JSON Patch array format.
Non-object request bodies return HTTP 400. Their HTTP route tests are mock-only;
the Docker parity server has its security plugin disabled.

## API boundaries

| Surface | Sync | Async | Limits |
| --- | --- | --- | --- |
| Document CRUD, bulk, mget, search, count | Implemented | Implemented | Selected request parameters only; mappings do not validate document types. |
| Alias CRUD and update_aliases | Implemented | Implemented | Updates apply sequentially, without transactional rollback or alias-filter evaluation. |
| Index create, exists, delete, refresh, stats | Implemented | Implemented | Refresh is a no-op; stats are placeholders. Async create does not retain mapping/settings metadata. |
| get_mapping, put_mapping, get_settings, put_settings | Implemented | Not implemented | Sync stores metadata rather than implementing schema enforcement. |
| indices.analyze | Empty token list | Not implemented | No full-text analysis engine. |
| cluster.health | Fixed response | Synchronous stub | Do not await the async fake's cluster.health. |
| suggest | Synthetic response | Synchronous stub | Text gets `_suggestion` appended; integers increment by one. |
| create_pit | Placeholder identifier | Not implemented | No point-in-time snapshot or PIT search implementation. |

`update` supports partial documents and no-op detection; scripted updates are not
implemented. `update_by_query` recognizes simple `ctx._source.field = params.value`
assignments, not the Painless language. Search scores and shard statistics are
placeholders. Bool/full-text query behavior and aggregation options are only partial.
Scrolls rerun the query against current state rather than preserving a snapshot.

Constructor patching does not change an `OpenSearch` class imported earlier with
`from opensearchpy import OpenSearch`; prefer `import opensearchpy` and construct
`opensearchpy.OpenSearch()` inside the decorated scope. The decorator blocks real
transport requests while it is active, so an inherited, unimplemented API method
fails instead of silently reaching a cluster. Direct fake instances do not install
that global transport guard. Client close/context-manager behavior is inherited.

The backend selector `OPENMOCK_TEST_BACKEND` belongs to this repository's test
harness; setting it does not change the public `@openmock` decorator into a real client.
