"""Run web and API together, and clean up both process groups on exit."""

import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
processes: list[subprocess.Popen] = []


def stop(*_: object) -> None:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
    raise SystemExit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        processes.append(
            subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "bottleiq.main:app",
                    "--reload",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                cwd=ROOT / "apps/api",
                start_new_session=True,
            )
        )
        processes.append(
            subprocess.Popen(
                ["npm", "run", "dev"], cwd=ROOT / "apps/web", start_new_session=True
            )
        )
        print(
            "BottleIQ: http://localhost:3000 | API: http://127.0.0.1:8000/docs",
            flush=True,
        )
        while all(process.poll() is None for process in processes):
            time.sleep(1)
    finally:
        stop()
