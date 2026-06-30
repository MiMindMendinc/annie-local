#!/usr/bin/env python3
"""Capture Annie UI frames for README demo GIF."""
from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("docs/assets/demo-frames")
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://127.0.0.1:8787"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 720})
        page.goto(URL, wait_until="networkidle")
        time.sleep(0.8)

        for i in range(8):
            page.screenshot(path=str(OUT / f"frame_{i:02d}.png"))
            time.sleep(0.35)

        # Simulate typing in input
        page.fill("#input", "help me plan the week")
        for i in range(8, 12):
            page.screenshot(path=str(OUT / f"frame_{i:02d}.png"))
            time.sleep(0.25)

        browser.close()

    print(f"Captured frames in {OUT}")


if __name__ == "__main__":
    main()
