#!/usr/bin/env python3
"""Capture reproducible Research Session screenshots from a running Annie server."""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import Page, sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8787", help="Running Annie URL.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/assets/research-session.png"),
        help="Desktop PNG destination.",
    )
    parser.add_argument(
        "--mobile-output",
        type=Path,
        help="Optional 390x844 mobile PNG destination.",
    )
    parser.add_argument(
        "--prompt",
        default="Verify this local research session.",
        help="Message to send before capture.",
    )
    parser.add_argument(
        "--chromium-executable",
        type=Path,
        help="Optional Chromium/Chrome binary; otherwise use Playwright's installed browser.",
    )
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    return parser.parse_args()


def capture(page: Page, url: str, prompt: str, output: Path, timeout_ms: int) -> None:
    page.goto(url, wait_until="networkidle", timeout=timeout_ms)
    page.locator("#input").fill(prompt)
    page.locator("#send").click()
    page.locator(".message-card.assistant").wait_for(state="visible", timeout=timeout_ms)
    page.locator("#voicePill[data-phase='idle']").wait_for(state="visible", timeout=timeout_ms)
    page.wait_for_timeout(500)
    page.locator("#input").blur()
    page.locator("#main").evaluate("node => { node.scrollTop = 0; }")
    output.parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(output), full_page=False)


def main() -> None:
    args = parse_args()
    with sync_playwright() as playwright:
        launch_args = {"executable_path": str(args.chromium_executable)} if args.chromium_executable else {}
        browser = playwright.chromium.launch(**launch_args)
        desktop = browser.new_page(viewport={"width": 1200, "height": 900})
        capture(desktop, args.url, args.prompt, args.output, args.timeout_ms)
        print(f"Captured {args.output}")

        if args.mobile_output:
            mobile = browser.new_page(
                viewport={"width": 390, "height": 844},
                device_scale_factor=1,
                is_mobile=True,
                has_touch=True,
            )
            capture(mobile, args.url, args.prompt, args.mobile_output, args.timeout_ms)
            print(f"Captured {args.mobile_output}")
        browser.close()


if __name__ == "__main__":
    main()
