# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
