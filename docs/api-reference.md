# API reference

This reference is built from the current Python source by mkdocstrings. Only
locally implemented public methods are listed; inherited opensearch-py methods
are not a promise of support. Read [API boundaries](unit-testing.md#api-boundaries)
for sync/async differences, placeholders, and unsupported features.

## Decorator

::: openmock.openmock

## Sync client

::: openmock.fake_opensearch.FakeOpenSearch

## Async client

::: openmock.fake_asyncopensearch.AsyncFakeOpenSearch

## Index clients

::: openmock.fake_indices.FakeIndicesClient

::: openmock.fake_asyncindices.FakeAsyncIndicesClient

## Cluster health

::: openmock.fake_cluster.FakeClusterClient

## Manual exploration server

::: openmock.fake_server.FakeOpenSearchServer

## Failure simulation

::: openmock.behaviour.server_failure
