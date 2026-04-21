# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.2.0] - 2025-12-04

### Added

- Ability to tell openmock to use a real server.
- Extra `openmock[web]`, which enables `openmock` cli command which runs a web UI for a web console for openmock.
- Included `openmock gui` which also is a dashboard, but uses standard library tkinter
- delete_by_query: searches for matching docs and deletes them, returning standard OpenSearch response format (sync +
  async)
- track_total_hits: added to @query_params on search in both sync and async clients
- exists_alias: checks if an alias exists, optionally scoped to a specific index (sync + async)
- update_aliases: atomic add/remove actions on aliases (sync + async)
- Enhanced get_alias: when index=None returns all indices with aliases; when name is provided, filters to only matching
  alias names
- _normalize_index_to_list in both fake_indices.py and fake_opensearch.py (and async variants) now checks the aliases
  dict and resolves alias names to their backing indices, so search, count,
  delete_by_query, and all other operations transparently work with alias names
- rest bridge to access open mock with http interface, install via `openmock[rest]` or `openmock[all]`

### Changed

- Behaviors changed to better match real opensearch

### Fixed

- Various issues found when running tests against OpenSearch.
- More unit tests, some based on those used by the opensearch-py library

## [3.1.5] - 2025-12-04

### Added

- Support `create_pit`

## [3.0.0] - 2023-08-21

### Fixed

- Both `@openmock` and  `@server_failure` decorators now work with async functions.

## [3.0.0] - 2023-08-21

### Added

- Async support
- Add `__all__` export declaration

### Fixed

- Bug related to attribute namespacing.

## [2.5.0] - 2023-12-12

### Fixed

- doc_type is gone from `opensearch-py` so it is also gone from openmock.
- Update build script
- Check python 3.13 support

## [2.3.6] - 2023-12-12

### Added

- Update function (Thanks!)
- tox runs against full matrix
- Range queries (Thanks!)

## [2.0.0] - 2023-04-28

### Added

- Fork to support opensearch-py
