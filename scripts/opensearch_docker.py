import argparse
import http.client
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

DEFAULT_CONTAINER_NAME = "openmock-opensearch-tests"
DEFAULT_IMAGE = "opensearchproject/opensearch:3.1.0"
DEFAULT_PORT = 9200
DEFAULT_WAIT_SECONDS = 120


def docker(*args: str, check: bool = True, capture_output: bool = False):
    if shutil.which("docker") is None:
        raise RuntimeError("Docker is required but was not found on PATH.")

    return subprocess.run(
        ["docker", *args],
        check=check,
        capture_output=capture_output,
        text=True,
    )


def endpoint_url(port: int) -> str:
    return f"http://localhost:{port}"


def container_exists(name: str) -> bool:
    result = docker("container", "inspect", name, check=False, capture_output=True)
    return result.returncode == 0


def remove_container(name: str) -> None:
    if container_exists(name):
        docker("rm", "--force", name)


def wait_for_opensearch(port: int, timeout_seconds: int) -> None:
    url = endpoint_url(port)
    deadline = time.time() + timeout_seconds
    last_error = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if response.status == 200 and payload.get("version", {}).get("number"):
                return
        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            http.client.RemoteDisconnected,
        ) as exc:
            last_error = exc
        time.sleep(1)

    raise RuntimeError(
        f"OpenSearch did not become ready at {url} within {timeout_seconds} seconds."
    ) from last_error


def start_container(args) -> None:
    remove_container(args.name)
    docker(
        "run",
        "--detach",
        "--name",
        args.name,
        "--publish",
        f"{args.port}:9200",
        "--env",
        "discovery.type=single-node",
        "--env",
        "DISABLE_INSTALL_DEMO_CONFIG=true",
        "--env",
        "DISABLE_SECURITY_PLUGIN=true",
        "--env",
        "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m",
        args.image,
    )
    wait_for_opensearch(args.port, args.wait_seconds)
    print(f"OpenSearch is ready at {endpoint_url(args.port)}")


def stop_container(args) -> None:
    remove_container(args.name)
    print(f"Removed container {args.name}")


def status_container(args) -> None:
    if not container_exists(args.name):
        print("stopped")
        return

    inspect = docker("container", "inspect", args.name, capture_output=True)
    data = json.loads(inspect.stdout)[0]
    running = data.get("State", {}).get("Running", False)
    print("running" if running else "stopped")


def run_tests(args) -> int:
    start_container(args)
    env = os.environ.copy()
    env["OPENMOCK_TEST_BACKEND"] = "real"
    env["OPENMOCK_REAL_OPENSEARCH_URL"] = endpoint_url(args.port)
    pytest_args = args.pytest_args or ["tests", "-m", "parity"]

    try:
        result = subprocess.run(
            ["uv", "run", "python", "-m", "pytest", *pytest_args],
            env=env,
            check=False,
        )
        return result.returncode
    finally:
        if not args.keep_container:
            remove_container(args.name)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Manage a Dockerized OpenSearch instance for parity tests."
    )
    parser.set_defaults(func=None)
    subparsers = parser.add_subparsers(dest="command")

    for command_name in ("start", "stop", "status", "test"):
        subparser = subparsers.add_parser(command_name)
        subparser.add_argument("--name", default=DEFAULT_CONTAINER_NAME)
        subparser.add_argument("--port", type=int, default=DEFAULT_PORT)
        if command_name in {"start", "test"}:
            subparser.add_argument("--image", default=DEFAULT_IMAGE)
            subparser.add_argument("--wait-seconds", type=int, default=DEFAULT_WAIT_SECONDS)
        if command_name == "test":
            subparser.add_argument(
                "--keep-container",
                action="store_true",
                help="Leave the container running after pytest exits.",
            )
            subparser.add_argument("pytest_args", nargs=argparse.REMAINDER)

    subparsers.choices["start"].set_defaults(func=start_container)
    subparsers.choices["stop"].set_defaults(func=stop_container)
    subparsers.choices["status"].set_defaults(func=status_container)
    subparsers.choices["test"].set_defaults(func=run_tests)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.func is None:
        parser.print_help()
        return 1

    try:
        result = args.func(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    raise SystemExit(main())
