# Web UI, desktop GUI, and REST bridge

Openmock includes three tools for exploring the fake backend interactively:

- a **Tkinter desktop GUI** in `openmock.gui` — no extra dependencies,
- a **Streamlit management console** in `openmock.web`,
- a **FastAPI REST bridge** in `scripts/rest_bridge.py`.

All three are meant for development and debugging. They are not production services.

## Tkinter desktop GUI

The Tkinter GUI ships with the base package and requires no extra dependencies beyond Python's standard `tkinter` module.

Start it with:

```bash
openmock gui
```

or:

```bash
uv run openmock gui
```

## What the web UI is

The Streamlit app creates a `FakeOpenSearch` instance and keeps it in `st.session_state`. That gives the UI a live in-memory backend you can inspect and mutate from the browser.

The web UI requires the optional web extras:

```bash
pip install openmock[web]
```

Start it with:

```bash
just web
```

or:

```bash
uv run openmock
```

or:

```bash
uv run streamlit run -m openmock.web
```

## What you can do in the UI

Both the Tkinter GUI and the Streamlit app expose the same six tabs:

| Tab | Purpose |
| --- | --- |
| `Indices` | Inspect current indices and documents, then add a document with JSON input. |
| `Search Sandbox` | Run a JSON search body against the fake and inspect hits and aggregations. |
| `Cluster Stats` | View fake cluster health and info responses. |
| `CAT` | Preview fake `_cat` output as either a text table or JSON. |
| `Security` | Manage fake users and roles with permissive CRUD and no auth checks. |
| `Ingest` | Create fake ingest pipelines, simulate them, and use them during indexing. |

The sidebar also lets you:

- toggle simulated server failure,
- reset the fake to a brand-new empty instance.

## Important limitation: UI state is local to the app process

Neither the Tkinter GUI nor the Streamlit app automatically shows the state from your unit tests.

That is because:

- the decorator-backed fake in tests lives in the test process,
- each UI tool creates its own fake in its own process,
- each process has separate in-memory state.

So the UI is best for manual exploration of Openmock behavior, not for inspecting a test that is already running somewhere else.

## REST bridge

The REST bridge exposes a small HTTP facade over a `FakeOpenSearch` instance. This is useful for tools that want to speak HTTP instead of using the Python client directly.

Start it with:

```bash
just run-mock-server
```

or:

```bash
uv run python scripts/rest_bridge.py
```

It listens on `http://localhost:9201`.

## Supported bridge endpoints

The bridge currently exposes a focused subset:

- `GET /` - fake cluster info
- `GET /_cluster/health` - fake cluster health
- `POST /{index}/_doc` and `PUT /{index}/_doc/{id}` - index a document, optionally with `?pipeline=...`
- `POST` or `PUT /{index}/_create/{id}` - create a document, optionally with `?pipeline=...`
- `GET` or `POST /{index}/_search` - search an index
- `GET /{index}/_count` and `GET /_count` - count documents
- `GET /_cat/indices` and `GET /_cat/count` - text or JSON cat output
- `GET|PUT|PATCH|DELETE /_plugins/_security/api/internalusers...` - fake user CRUD
- `GET|PUT|PATCH|DELETE /_plugins/_security/api/roles...` - fake role CRUD
- `GET|PUT|DELETE /_ingest/pipeline...` and `POST /_ingest/pipeline/.../_simulate` - fake ingest pipelines

The legacy `_opendistro/_security/...` aliases are also accepted for the security routes.

Examples:

```bash
curl -X POST http://localhost:9201/books/_doc -H "Content-Type: application/json" -d "{\"title\":\"Docs\",\"category\":\"guide\"}"
```

```bash
curl -X POST http://localhost:9201/books/_search -H "Content-Type: application/json" -d "{\"query\":{\"match\":{\"title\":\"Docs\"}}}"
```

## How the UI and bridge relate

They both use Openmock as the backend, but they do not share state unless they are wired to the same in-process fake instance. As currently implemented:

- the Streamlit app has its own fake,
- the FastAPI bridge has its own fake,
- your tests have their own fake.

Treat them as separate manual workbenches backed by the same fake implementation.

## Good uses

- trying out supported query shapes,
- debugging fake behavior manually,
- demonstrating Openmock to teammates,
- smoke-testing integrations that only know how to speak HTTP.

## Less suitable uses

- verifying production-level OpenSearch compatibility,
- sharing persistent state across tools or processes,
- replacing parity tests against a real cluster.
