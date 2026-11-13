"""Docker startup polling must tolerate transient failures without hiding timeouts."""

import http.client
import urllib.error
from unittest.mock import MagicMock, Mock

import pytest

from scripts import opensearch_docker as runner


def response(body=b'{"version": {"number": "3.9.0"}}'):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status = 200
    result.read.return_value = body
    return result


@pytest.mark.parametrize(
    "error",
    [
        ConnectionResetError(104, "Connection reset by peer"),
        http.client.RemoteDisconnected("startup"),
        urllib.error.URLError("connection refused"),
        TimeoutError("startup"),
    ],
)
@pytest.mark.parametrize("during_read", [False, True])
def test_polling_retries_transient_network_failures(monkeypatch, error, during_read):
    first = response()
    first.read.side_effect = error
    opener = Mock(side_effect=[first if during_read else error, response()])
    monkeypatch.setattr(runner.urllib.request, "urlopen", opener)
    monkeypatch.setattr(runner.time, "monotonic", Mock(side_effect=[0, 0, 1]))
    sleep = Mock()
    monkeypatch.setattr(runner.time, "sleep", sleep)

    runner.wait_for_opensearch(19200, 5)

    assert opener.call_count == 2
    sleep.assert_called_once_with(1)


def test_polling_retries_invalid_json_and_missing_version(monkeypatch):
    opener = Mock(side_effect=[response(b"not ready"), response(b"{}"), response()])
    monkeypatch.setattr(runner.urllib.request, "urlopen", opener)
    monkeypatch.setattr(runner.time, "monotonic", Mock(side_effect=[0, 0, 1, 2]))
    monkeypatch.setattr(runner.time, "sleep", Mock())
    runner.wait_for_opensearch(19200, 5)
    assert opener.call_count == 3


def test_persistent_reset_times_out_with_original_cause(monkeypatch):
    error = ConnectionResetError(104, "Connection reset by peer")
    opener = Mock(side_effect=error)
    monkeypatch.setattr(runner.urllib.request, "urlopen", opener)
    monkeypatch.setattr(runner.time, "monotonic", Mock(side_effect=[0, 0, 1, 2]))
    monkeypatch.setattr(runner.time, "sleep", Mock())

    with pytest.raises(RuntimeError, match="within 2 seconds") as caught:
        runner.wait_for_opensearch(19200, 2)
    assert caught.value.__cause__ is error
    assert opener.call_count == 2


@pytest.mark.parametrize("keep", [False, True])
def test_startup_timeout_logs_and_cleans_up_unless_kept(monkeypatch, keep):
    args = runner.build_parser().parse_args(["test"])
    args.keep_container = keep
    remove = Mock()
    docker = Mock()
    run = Mock()
    monkeypatch.setattr(runner, "remove_container", remove)
    monkeypatch.setattr(runner, "docker", docker)
    monkeypatch.setattr(runner.subprocess, "run", run)
    monkeypatch.setattr(
        runner, "wait_for_opensearch", Mock(side_effect=RuntimeError("not ready"))
    )

    with pytest.raises(RuntimeError, match="not ready"):
        runner.run_tests(args)

    docker.assert_any_call("logs", "--tail", "100", args.name, check=False)
    # start_container removes an old container before creating the test container.
    assert remove.call_count == (1 if keep else 2)
    run.assert_not_called()
