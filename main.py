"""Replit entrypoint — boots Annie-5 on 0.0.0.0:8787."""
from __future__ import annotations

import subprocess
import sys


def main() -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "annie.cli",
            "launch",
            "--host",
            "0.0.0.0",
            "--port",
            "8787",
            "--no-browser",
            "--model",
            "llama3.2",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
