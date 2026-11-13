# Contributing

This guide is for contributors working on Openmock itself: the in-memory fake, the parity seam, the web tools, and the docs.

## Project goal

Openmock aims to be a practical, developer-friendly fake for `opensearch-py`. The focus is fast tests with realistic state transitions, not perfect emulation of every OpenSearch feature.

That tradeoff shapes most development decisions:

- preserve OpenSearch-shaped responses where practical,
- keep common test workflows fast and simple,
- add features when they help real tests,
- use parity tests against a live backend to check important behavior.

## Local setup

This repo uses `uv`.

```bash
uv sync --all-extras
```

That installs runtime, development, and optional web dependencies.

## Common commands

Prefer the existing project commands instead of ad hoc one-offs.

| Task | Command |
| --- | --- |
| Sync dependencies | `uv sync --all-extras` |
| Run tests | `uv run python -m pytest tests` |
| Run parity tests against Docker OpenSearch | `uv run python scripts/opensearch_docker.py test` |
| Run the full Makefile unit checks | `uv run --all-extras python scripts/check.py` |
| Run formatting and pre-commit checks | `make pre-commit` |
| Run the Streamlit UI | `just web` |
| Run the HTTP bridge | `just run-mock-server` |
| Build the package | `uv build` |

## Development workflow

The normal loop is:

1. update code or tests,
1. run `uv run pytest tests`,
1. for behavior-sensitive changes, run the real-backend parity flow,
1. check formatting and linting with the existing project commands.

If you change documentation in `docs/`, format it with:

```bash
uv run mdformat README.md docs/*.md
```

## Repository tour

### `openmock/__init__.py`

This is the main entrypoint. It exports the decorator and fake classes, and it patches `opensearchpy.OpenSearch` / `AsyncOpenSearch` during decorated tests.

It also holds the host-keyed caches that make repeated client construction reuse the same fake instance inside one test scope.

### `openmock/fake_opensearch.py`

This is the core sync implementation. It stores indexed documents in memory, implements most of the fake client surface, and evaluates search queries against stored documents.

If you are changing behavior for indexing, updates, search, aggregations, scroll, suggest, or response shaping, this is usually the first file to inspect.

### `openmock/fake_asyncopensearch.py`

This mirrors the sync fake for async code. Most new sync behavior needs an async counterpart here as well.

When fixing bugs, check both files unless the behavior is intentionally sync-only.

### `openmock/fake_indices.py` and `openmock/fake_cluster.py`

These implement the sub-clients reachable as `client.indices` and `client.cluster`.

They are small, but important for keeping the fake usable by real application code that expects the normal client shape.

### `openmock/behaviour/`

Behavior toggles live here. Right now the main one is `server_failure`, which short-circuits fake methods with a 500-like response payload.

This is the place for small opt-in test behaviors that should apply across fake client methods.

### `openmock/utilities/`

Helpers shared by the fake implementations live here, including decorators and ID utilities.

Check for reusable helpers here before duplicating logic in the client classes.

### `openmock/gui.py`

This is the Tkinter desktop GUI. It requires Tk support and a graphical display, but no extra Python package. It exposes the same six-tab interface as the Streamlit app.

Changes here should keep the UI simple and clearly development-oriented.

### `openmock/cli.py`

This is the top-level CLI dispatcher for the `openmock` command. `openmock gui` launches the Tkinter GUI; `openmock` (no arguments) launches the Streamlit web UI.

### `openmock/web.py`

This is the Streamlit management console. It is a lightweight manual frontend over a `FakeOpenSearch` instance.

Changes here should keep the UI simple and clearly development-oriented.

### `openmock/rest_bridge.py`

This file exposes a narrow HTTP facade over the fake so non-Python tools can interact with it. It is useful for manual testing and demos, not as a production API server. It is launched via `openmock serve`.

### `tests/`

The tests are the clearest executable specification of supported behavior.

Key areas:

- `tests/fake_opensearch/` - sync fake behavior,
- `tests/fake_asyncopensearch/` - async fake behavior,
- `tests/fake_indices/` and `tests/fake_cluster/` - sub-client behavior,
- `tests/backend.py` - the seam that can switch the test suite from fake to a real OpenSearch backend.

If you are unsure what a method should do, start by finding or adding a test here.

## Parity testing

The repository supports running a parity-focused subset against a real OpenSearch backend. That path is driven by `tests/backend.py` and the `OPENMOCK_TEST_BACKEND=real` seam.

Use it when:

- you are implementing behavior intended to match real OpenSearch closely,
- a fake-vs-real mismatch is suspected,
- you are changing query or bulk semantics.

The Docker helper is:

```bash
uv run --all-extras python scripts/opensearch_docker.py test
```

There are also `just` commands for starting and stopping a local real backend.

## Adding or changing behavior

When extending Openmock:

1. add or update tests first,
1. keep response shapes close to the client behavior that application code expects,
1. update both sync and async fakes when appropriate,
1. document notable user-facing changes in the docs and changelog if needed.

## Documentation layout

User-facing docs belong under `docs/` as Markdown for the MkDocs site hosted on Read the Docs.

The API reference is generated from current source by mkdocstrings during each build; do not check in generated HTML.

## Maintenance release checks

Use `uv run --all-extras python scripts/check.py` (also `make check-llm` or
`just check-llm`) for concise Ruff, Black, mypy, pylint, Bandit and coverage checks.
The runner uses Python subprocesses and works without a POSIX shell. CI runs it
on Windows, Linux and macOS with Python 3.11, 3.14 and 3.15, then builds packages.
A separate Linux job runs the parity subset against OpenSearch 3.9.0 in Docker.

The current verified client is opensearch-py 3.2.0; tox also retains 2.8.0 coverage.
See the [compatibility results](compatibility.md)
for locally executed combinations. To compare another server release, pass
`--image opensearchproject/opensearch:<version>` to the Docker runner's `test` command.

## Changelog and release automation

Write one changelog bullet per change, on one physical line, under Added,
Changed, or Fixed in `CHANGELOG.md`. Run `uv run kaclm validate --strict`;
this also runs as part of `scripts/check.py`.

The workflows follow `keepachangelog-manager`:

1. Push to main refreshes a GitHub draft release from Unreleased using `kaclm github-release`.
2. Publishing that draft triggers `.github/workflows/publish_to_pypi.yml`.
3. `kaclm release-bump` updates the changelog and `pyproject.toml`, pushes a release branch, and opens a PR.
4. The build job checks out that branch, runs release checks, builds and validates distributions, then uploads artifacts.
5. The publish job uploads those artifacts to PyPI with trusted publishing; merge the release PR after publication succeeds.

Publishing the draft is the release gate. The previous standalone manual PyPI
workflow has been replaced; it did not manage the changelog or bump versions.
Repository Actions must be allowed to create PRs, and the existing PyPI trusted
publisher must authorize `publish_to_pypi.yml` with the `pypi` environment.

`uv run kaclm version --reference future` currently proposes **3.3.0** because
Unreleased includes Added entries. No version has been bumped locally.

## Build the documentation and homepage

```shell
uv run --with-requirements docs/requirements.txt mkdocs build --strict
hugo --source landing --minify --gc
```

MkDocs builds the detailed guides and source-based API reference into `site/`.
Read the Docs uses `.readthedocs.yaml`; the GitHub docs job checks the same strict
build. Hugo builds the independent landing page into `landing/public/`, modeled on
terminaltables3. Use Hugo 0.169.0, as pinned in `.github/workflows/pages.yml`.
For a local preview, run `hugo server --source landing`.

The Pages workflow builds pull requests and deploys only pushes/manual runs on
main. Set repository Settings → Pages → Source to **GitHub Actions** once.
The homepage links to RTD, PyPI and GitHub; it does not duplicate the API manual.

Run `make gha-upgrade` to refresh action versions and full commit pins, validate
workflow structure, and run zizmor. `uv run --with zizmor zizmor --persona pedantic .github/workflows`
runs the audit directly. Supply a GitHub token through `GH_TOKEN` for online checks; without one, zizmor runs offline. The dedicated CI audit uses pinned zizmor 1.32.0;
upgrade that pin when refreshing the audit tool.
