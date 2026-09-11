"""Replit entrypoint with exact startup authorization for its webview."""

from __future__ import annotations

import os
import re
import subprocess
import sys

_DNS_LABEL = re.compile(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\Z")


def _launch_environment() -> dict[str, str]:
    env = os.environ.copy()
    domain = env.get("REPLIT_DEV_DOMAIN")
    if domain is None:
        return env
    # This is trusted startup configuration, never a request or forwarded header.
    # Accept one bare DNS hostname; URLs, ports, wildcards and lists fail closed.
    if len(domain) > 253 or "." not in domain or any(not _DNS_LABEL.fullmatch(label) for label in domain.split(".")):
        raise ValueError("REPLIT_DEV_DOMAIN must be one bare DNS hostname without a scheme, port, or path")
    origin = f"https://{domain.lower()}"
    configured = env.get("CORS_ORIGINS", "http://127.0.0.1:8787,http://localhost:8787")
    origins = [value.strip() for value in configured.split(",") if value.strip()]
    if origin not in origins:
        origins.append(origin)
    env["CORS_ORIGINS"] = ",".join(origins)
    return env


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
        env=_launch_environment(),
    )


if __name__ == "__main__":
    main()
