#!/usr/bin/env python3
"""Source-checkout entry point for the packaged Annie WOPR bridge."""

from annie.wopr_server import main

if __name__ == "__main__":
    raise SystemExit(main())
