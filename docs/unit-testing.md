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

- two clients created with the same host configuration share the same in-memory data,
- a different host or port gives you a separate fake instance,
- each decorated test starts with a clean fake.

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
- `suggest`,
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

**Not supported** (will silently return no results or empty aggregations):

- `wildcard`, `prefix`, `fuzzy`, `regexp` queries,
- `nested` and `geo` queries,
- `script` queries and aggregations,
- numeric aggregations (`avg`, `sum`, `min`, `max`, `percentiles`),
- `date_histogram` and `histogram` aggregations,
- relevance scoring (`_score` is not populated),
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
