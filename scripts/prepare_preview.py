"""Copy the active Python runtime into the checkout for a restricted UI preview.

Optional: normal development uses .venv directly. Run with .venv/bin/python.
The copied runtime, installed dependencies, and preview data stay git-ignored.
"""

from __future__ import annotations

import json
import shutil
import sys
import sysconfig
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if sys.platform != "linux":
        raise SystemExit("This optional preview helper requires Linux. Use .venv directly on other platforms.")
    packages = Path(sysconfig.get_path("purelib")).resolve()
    try:
        relative_packages = packages.relative_to(root)
    except ValueError as exc:
        raise SystemExit("Run this helper with the checkout's .venv/bin/python.") from exc
    target = root / ".preview-python"
    (target / "bin").mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(sys.executable).resolve(), target / "bin" / "python")
    version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    shutil.copytree(
        Path(sysconfig.get_path("stdlib")),
        target / "lib" / version,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "site-packages", "__pycache__", "test", "tests", "tkinter", "turtledemo", "idlelib", "ensurepip"
        ),
    )
    for library in (Path(sys.base_prefix) / "lib").glob("libpython*.so*"):
        if library.is_file():
            shutil.copy2(library, target / "lib" / library.name)
    (target / "runtime.json").write_text(json.dumps({"sitePackages": relative_packages.as_posix()}), encoding="utf-8")
    print("Preview runtime prepared. Run npm run dev or your supervised preview command.")


if __name__ == "__main__":
    main()
