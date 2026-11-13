# Getting started

Openmock requires Python 3.11 or newer. Add it to your application's test dependencies:

```shell
uv add --dev openmock pytest pytest-asyncio
```

For an existing virtual environment, `uv pip install openmock` also works. The
base package supports sync and async clients; optional extras add interactive tools.

## A complete sync test

Save this as `test_search.py`:

```python
import opensearchpy
from openmock import openmock


@openmock
def test_find_a_book():
    client = opensearchpy.OpenSearch()
    client.index(index="books", id="1", body={"title": "Dune"})
    result = client.search(index="books", body={"query": {"match": {"title": "Dune"}}})
    assert result["hits"]["total"]["value"] == 1
    assert result["hits"]["hits"][0]["_source"]["title"] == "Dune"
```

Run `uv run pytest test_search.py`. No OpenSearch process or Docker container is
needed. Instantiate clients inside the decorated function and use
`opensearchpy.OpenSearch` rather than a class imported before the patch.

## An async test

```python
import opensearchpy
import pytest
from openmock import openmock


@pytest.mark.asyncio
@openmock
async def test_get_a_book():
    client = opensearchpy.AsyncOpenSearch()
    try:
        await client.index(index="books", id="1", body={"title": "Dune"})
        result = await client.get(index="books", id="1")
        assert result["_source"]["title"] == "Dune"
    finally:
        await client.close()
```

Sync and async clients have separate in-memory stores. Most document operations
exist in both, but some sub-client APIs differ; consult the
[API boundaries](unit-testing.md#api-boundaries) before relying on an inherited method.

## Choose a tool

| Need | Install | Run |
| --- | --- | --- |
| Unit tests | `uv add --dev openmock` | `@openmock` |
| Browser management console | `uv add --dev "openmock[web]"` | `uv run openmock` |
| Local HTTP facade | `uv add --dev "openmock[rest]"` | `uv run openmock serve` |
| Desktop inspector | Base package plus Tk/display support | `uv run openmock gui` |

The CLI also supports `uv run openmock --help` and `--version` without starting a UI.
The inspectors run in their own processes and do not show a test's live state.

## Decide what to verify with a real server

Use the fake for fast tests of document workflows. Use a real OpenSearch backend
for analyzer behavior, relevance scoring, advanced queries, security, concurrency,
or exact error contracts. See [supported behavior](unit-testing.md),
[tested versions](compatibility.md), and [contributor parity testing](contributing.md#parity-testing).
