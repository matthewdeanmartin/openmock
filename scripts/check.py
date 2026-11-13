"""Run release checks with concise output on Windows, macOS, and Linux."""

import subprocess
import sys


def main() -> int:
    checks = [
        ("changelog", ["changelogmanager", "validate", "--strict"]),
        ("ruff", ["ruff", "check", "."]),
        ("black", ["black", "--check", "openmock", "tests", "scripts"]),
        ("mypy", ["mypy", "openmock"]),
        ("pylint", ["pylint", "openmock", "--fail-under", "10"]),
        ("bandit", ["bandit", "-q", "-r", "openmock"]),
        (
            "pytest",
            [
                "pytest",
                "tests",
                "-q",
                "--disable-warnings",
                "--cov=openmock",
                "--cov-report=term",
                "--cov-fail-under=85",
            ],
        ),
    ]
    for name, args in checks:
        result = subprocess.run(
            [sys.executable, "-m", *args], capture_output=True, text=True, check=False
        )
        print(f"{name}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
        if result.returncode or name == "pytest":
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
