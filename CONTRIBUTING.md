# Contributing

## Project goals

The old elasticmock might be an inspiration for new features, but I don't have the spare time to keep it "merge compatible", so I won't be merging code directly from elasticmock.

## Setup

Dependencies
```bash
pipenv install --dev
pipenv shell
```

Poetry might work, too.

## Checks and Tests

Minimal expectations.
```bash
black .
pylint openmock
pytest tests
```

On gitlab, it will run tox and check against python 3.6 thru 3.11 all versions of openmock.

See [build.yaml](.github/workflows/build.yaml) and [tox.yaml](.github/workflows/tox.yaml)