# Verified compatibility — 2026-11-12

The maintenance checks used **opensearch-py 3.2.0** and a real Dockerized
**OpenSearch 3.9.0** (`opensearchproject/opensearch:3.9.0`), the latest stable
releases listed by [PyPI](https://pypi.org/project/opensearch-py/) and
[OpenSearch](https://opensearch.org/artifacts/by-version/) on the verification date.

| Python | opensearch-py | Backend | Result |
| --- | --- | --- | --- |
| 3.15.0 | 3.2.0 | In-memory mock, REST, GUI and web tests | 328 passed |
| 3.15.0 | 3.2.0 | OpenSearch 3.9.0 in Docker | 45 parity tests passed |
| 3.14.7 | 3.2.0 | In-memory mock, REST, GUI and web tests | 328 passed |
| 3.11.9 | 2.8.0 | In-memory mock, REST, GUI and web tests | 328 passed |

These runs were performed on Windows; the CI matrix also covers Linux and macOS.
The full suite reaches 89.31% statement coverage (REST bridge: 97%). Mypy 2.4.1,
pylint 4.1.3, Ruff 0.17.5, Black and Bandit pass. Wheel and source distribution
builds pass. Python and runtime dependency minimums remain unchanged in this pass.
Python 3.15 now installs the optional web extra successfully, including pyarrow.

Reproduce the release checks and real-server comparison with:

```shell
uv run --all-extras python scripts/check.py
uv run --all-extras python scripts/opensearch_docker.py test
```

The Docker runner binds its test server to loopback and removes the container
when tests finish. Use `--port 19200` if port 9200 is occupied.

Parity covers selected implemented APIs, not the full OpenSearch product.
The new contract suite exercises raw sync and async clients without response
normalization; older compatibility tests still use the adapters in `tests/backend.py`.
See [unit-testing guidance](unit-testing.md) for scope and limitations.

## Lower-version tox verification

`uv run tox -e py311-opensearch12,py311-opensearchlatest` passes both environments:
Python 3.11.9 with opensearch-py 2.8.0 and 3.2.0, 328 tests in each.

Python 3.10 is excluded by this project's `requires-python = ">=3.11"`, changed
in commit `d20b26d` before this maintenance pass. Current opensearch-py 3.2.0
and aiohttp 3.14.5 still allow Python 3.10. Current
[python-dateutil 4.0.0](https://pypi.org/project/python-dateutil/4.0.0/) and
[Streamlit 1.67.0](https://pypi.org/project/streamlit/1.67.0/) require Python 3.11.
Older dependency releases could resolve on 3.10, but restoring project support
would require revisiting the declared floor, code compatibility, and tests.
