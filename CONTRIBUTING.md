# Contributing

Use Python 3.11 or newer and uv:

```shell
uv sync --all-extras
uv run --all-extras python scripts/check.py
```

Read the [contributor guide](docs/contributing.md) for the repository layout,
Docker parity testing, documentation builds, and the release workflow.
The old elasticmock project can inspire features, but this fork does not aim to
remain merge-compatible with it.

See [build.yml](.github/workflows/build.yml) and [tox.yml](.github/workflows/tox.yml)
for the current CI matrix. Keep meaningful changes in CHANGELOG.md, one bullet per
change on one physical line. Do not commit or push without explicit authorization.
