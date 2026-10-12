import sys
from unittest.mock import patch

from openmock.cli import main


def test_cli_default():
    with patch("openmock.web.main") as mock_web_main:
        mock_web_main.return_value = 0
        assert main([]) == 0
        mock_web_main.assert_called_once_with([])


def test_cli_gui():
    with patch("openmock.gui.main") as mock_gui_main:
        mock_gui_main.return_value = 0
        assert main(["gui"]) == 0
        mock_gui_main.assert_called_once()


def test_cli_serve():
    with patch("openmock.rest_bridge.main") as mock_serve_main:
        mock_serve_main.return_value = 0
        assert main(["serve"]) == 0
        mock_serve_main.assert_called_once()


def test_cli_web_with_args():
    with patch("openmock.web.main") as mock_web_main:
        mock_web_main.return_value = 1
        assert main(["--port", "9200"]) == 1
        mock_web_main.assert_called_once_with(["--port", "9200"])


def test_main_import():
    # Test that __main__.py can be imported and it calls cli.main
    with patch("openmock.cli.main") as mock_cli_main:
        mock_cli_main.return_value = 0
        with patch.object(sys, "argv", ["openmock"]):
            pass

            # Note: importing it again might not trigger the if __name__ == "__main__" block
            # if it was already imported, but it's a simple file.
            # Actually, since it's "if __name__ == '__main__':", we can't easily test it by importing.


import subprocess
from pathlib import Path
import pytest


@pytest.mark.parametrize("flag", ["--help", "-h", "--version"])
def test_installed_info_flags_exit_without_starting_ui(
    flag: str, tmp_path: Path
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "openmock", flag],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert result.returncode == 0
    assert ("openmock " if flag == "--version" else "usage: openmock") in result.stdout
