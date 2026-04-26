import os
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest


def subprocess_env():
    repo_root = Path(__file__).resolve().parents[4]
    paths = [
        str(repo_root / "packages" / "flotilla_fastapi" / "src"),
        str(repo_root / "packages" / "flotilla_core" / "src"),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    return env


def wait_for_server(url, timeout=10):
    start = time.time()

    while time.time() - start < timeout:
        try:
            r = httpx.get(url)
            if r.status_code == 200:
                return
        except Exception:
            pass

        time.sleep(0.2)

    raise RuntimeError("Server did not start")


@pytest.mark.integration
def test_hosted_uvicorn():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "packages.flotilla_fastapi.tests.integration.app_fixture:app",
            "--port",
            "8001",
        ],
        env=subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_server("http://127.0.0.1:8001/hello")

        response = httpx.get("http://127.0.0.1:8001/hello")
        assert response.status_code == 200
        assert response.text == '["hello world"]'

    finally:
        process.terminate()
        stdout, _ = process.communicate(timeout=10)
        print("\n==== UVICORN HOSTED OUTPUT ====\n")
        print(stdout)
        print("\n========================\n")


@pytest.mark.integration
def test_embedded_mode():
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "packages.flotilla_fastapi.tests.integration.app_fixture",
        ],
        env=subprocess_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        wait_for_server("http://127.0.0.1:8000/hello")

        response = httpx.get("http://127.0.0.1:8000/hello")
        assert response.status_code == 200

    finally:
        process.terminate()
        stdout, _ = process.communicate(timeout=10)
        print("\n==== UVICORN EMBEDDED OUTPUT ====\n")
        print(stdout)
        print("\n========================\n")

    assert "SHUTDOWN_HOOK_CALLED" in stdout
