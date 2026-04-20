from pathlib import Path

import pytest

PARITY_TEST_PATHS = {
    "tests/test_aggregations.py",
    "tests/test_from_opensearch_py/test_opensearch_py_compat.py",
    "tests/test_new_suites/test_all.py",
}


def _relative_test_path(item: pytest.Item, root_path: Path) -> str:
    return Path(str(item.path)).resolve().relative_to(root_path).as_posix()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    root_path = Path(str(config.rootpath)).resolve()
    for item in items:
        relative_path = _relative_test_path(item, root_path)
        if relative_path in PARITY_TEST_PATHS:
            item.add_marker(pytest.mark.parity)
            continue
        item.add_marker(pytest.mark.mock_backend)
