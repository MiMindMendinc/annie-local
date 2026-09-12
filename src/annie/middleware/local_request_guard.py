from __future__ import annotations

import re
from ipaddress import ip_address
from urllib.parse import urlsplit

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from annie.middleware.security_headers import SECURE_HEADERS

# Parse the raw authority before other middleware builds a URL from Host.
# Bracketed IPv6 is supported; credentials, paths and ambiguous headers are not.
_AUTHORITY = re.compile(r"(?:[a-zA-Z0-9.-]+|\[[a-fA-F0-9:.]+\])(?::[0-9]{1,5})?\Z")


def _hostname(authority: str) -> str | None:
    if not _AUTHORITY.fullmatch(authority):
        return None
    try:
        parsed = urlsplit(f"http://{authority}")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
        host = parsed.hostname
        try:
            return str(ip_address(host))
        except ValueError:
            return host
    except ValueError:
        return None


def _origin(value: str) -> tuple[str, str, int] | None:
    try:
        parsed = urlsplit(value)
        host = _hostname(parsed.netloc)
        if parsed.scheme not in {"http", "https"} or host is None:
            return None
        if parsed.path or parsed.query or parsed.fragment or value != f"{parsed.scheme}://{parsed.netloc}":
            return None
        return parsed.scheme, host, parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError:
        return None


class LocalRequestGuardMiddleware:
    """Reject foreign browser requests before they reach the unauthenticated API.

    CORS alone does not prevent side effects from simple cross-origin requests.
    Hosts come from configuration, never DNS lookups or forwarded headers.
    Origin-free CLI requests remain supported. This is not local-process auth.
    """

    def __init__(self, app: ASGIApp, *, host: str, port: int, cors_origins: tuple[str, ...]) -> None:
        self.app = app
        self.hosts = {"127.0.0.1", "localhost", "::1"}
        authority = f"[{host}]" if ":" in host and not host.startswith("[") else host
        configured_host = _hostname(authority)
        if configured_host is None:
            raise ValueError("local bind host must be a hostname or IP address")
        try:
            wildcard_bind = ip_address(configured_host).is_unspecified
        except ValueError:
            wildcard_bind = False
        # A wildcard listen address does not authorize arbitrary Host headers.
        if not wildcard_bind:
            self.hosts.add(configured_host)
        self.origins = {("http", name, port) for name in self.hosts}
        for value in cors_origins:
            origin = _origin(value)
            if origin is None:
                raise ValueError("local CORS_ORIGINS must contain exact http:// or https:// origins without paths")
            self.origins.add(origin)
            self.hosts.add(origin[1])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        hosts = [value.decode("latin-1") for name, value in scope["headers"] if name.lower() == b"host"]
        origins = [value.decode("latin-1") for name, value in scope["headers"] if name.lower() == b"origin"]
        status = 0
        detail = ""
        if len(hosts) != 1 or _hostname(hosts[0]) not in self.hosts:
            status, detail = 400, "Host is not allowed for this local instance."
        elif origins and (len(origins) != 1 or _origin(origins[0]) not in self.origins):
            status, detail = 403, "Origin is not allowed for this local instance."
        if status:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                response = JSONResponse(
                    {"detail": detail},
                    status_code=status,
                    headers={**SECURE_HEADERS, "Cache-Control": "no-store", "Pragma": "no-cache"},
                )
                await response(scope, receive, send)
            return
        # Leave request bodies, streaming events and disconnects untouched.
        await self.app(scope, receive, send)
