from __future__ import annotations

import re
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlsplit

_CONTAINER_HOSTS = {"ollama", "postgres", "redis", "minio"}
_HOST_BRIDGES = {"host.docker.internal", "host.containers.internal"}


def classify_endpoint(url: str | None) -> str:
    """Classify a configured endpoint without exposing credentials or host details."""

    if not url:
        return "unknown"
    try:
        host = (urlsplit(url).hostname or "").strip().lower()
    except ValueError:
        return "unknown"
    if not host:
        return "unknown"
    if host == "localhost":
        return "loopback"
    if host in _HOST_BRIDGES:
        return "host"
    if host in _CONTAINER_HOSTS:
        return "container"
    try:
        address = ip_address(host)
    except ValueError:
        return "remote"
    if address.is_loopback:
        return "loopback"
    if address.is_private or address.is_link_local:
        return "lan"
    return "remote"


def trust_environment_proxy(url: str | None) -> bool:
    """Use host proxy settings only for explicitly remote routes."""

    return classify_endpoint(url) == "remote"


def _locality(route: str) -> str:
    if route in {"loopback", "host"}:
        return "device"
    if route == "container":
        return "local_container"
    if route == "lan":
        return "local_network"
    if route == "remote":
        return "remote"
    return "unknown"


def _model_key(name: Any) -> str:
    value = str(name or "").strip().lower()
    value = value.removeprefix("registry.ollama.ai/")
    value = value.removeprefix("library/")
    return value.removesuffix(":latest")


def match_model(configured: str, names: list[str]) -> dict[str, Any]:
    """Resolve only exact canonical aliases or one unambiguous tag family."""
    key = _model_key(configured)
    exact = [name for name in names if _model_key(name) == key]
    candidates = exact or [name for name in names if key and _model_key(name).startswith(key + ":")]
    resolved = candidates[0] if len(candidates) == 1 else None
    return {
        "installed": resolved is not None,
        "resolved_name": resolved,
        "candidates": candidates,
        "nearest_installed": (candidates or names or [None])[0],
    }


def public_endpoint(url: str) -> str:
    """Keep diagnostics useful without copying endpoint credentials into health."""
    try:
        parts = urlsplit(url)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            return "invalid endpoint"
        return parts._replace(netloc=parts.netloc.rsplit("@", 1)[-1], query="", fragment="").geturl().rstrip("/")
    except ValueError:
        return "invalid endpoint"


def model_repair(name: str, url: str, backend: dict[str, Any]) -> dict[str, Any]:
    url = public_endpoint(url)
    match = match_model(name, backend.get("model_names") or [])
    reachable = backend.get("endpoint_available", backend.get("ok", False))
    if not reachable:
        code, title = "endpoint_down", "Connect your model"
        detail = (
            f'Ollama is unavailable at {url}. Selected model: "{name}". Start Ollama or check the endpoint, then retry.'
        )
    elif match["installed"]:
        code, title = "ready", "Your model is ready"
        detail = f"{match['resolved_name']} is available at {url}."
    elif backend.get("model_names"):
        code, title = "name_mismatch", "Choose an installed model"
        detail = f'Configured "{name}" does not resolve to one installed tag at {url}.'
    else:
        code, title = "model_missing", "Pull your first model"
        detail = f'Ollama is reachable at {url}, but "{name}" is not installed.'
    # Model names are CLI arguments, not shell programs. Quote unsafe characters
    # for both the documented POSIX shell and PowerShell examples.
    safe_name = name if re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./:-]*", name) else ""
    command = f"ollama pull {safe_name}"
    return {
        "code": code,
        "title": title,
        "detail": detail,
        "actions": [
            {"id": "retry", "label": "Retry health"},
            {"id": "open_settings", "label": "Choose installed model"},
            {"id": "copy_pull", "label": f"Copy: {command}", "command": command if safe_name else ""},
        ],
    }


def build_runtime_status(
    *,
    mode: str,
    runtime: dict[str, Any],
    backend: dict[str, Any],
    voice: dict[str, Any],
    service_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build conservative, evidence-based labels for the UI.

    This deliberately never returns ``offline_verified``. A collection of local
    routes is not proof that the operating system or browser has no network path.
    """

    model_route = classify_endpoint(str(runtime.get("ollama_url") or ""))
    voice_route = classify_endpoint(str(runtime.get("voice_url") or ""))
    model_locality = _locality(model_route)
    voice_locality = _locality(voice_route)
    endpoint_available = bool(backend.get("endpoint_available", backend.get("ok")))
    available_names = backend.get("model_names")
    model_installed: bool | None = None
    if isinstance(available_names, list):
        model_installed = match_model(str(runtime.get("model") or ""), available_names)["installed"]
    model_ready = endpoint_available and model_installed is not False
    bridge_ready = bool(voice.get("bridge_ok"))

    routes: dict[str, str] = {
        "model": model_route,
        "voice": voice_route,
    }
    if mode == "production":
        for name, url in (service_urls or {}).items():
            routes[name] = classify_endpoint(url)

    remote_names = sorted(name for name, route in routes.items() if route == "remote")
    uncertain_names = sorted(name for name, route in routes.items() if route in {"lan", "unknown"})
    if remote_names:
        network_claim = "remote_configured"
        network_reason = f"Remote route configured for: {', '.join(remote_names)}."
    elif uncertain_names:
        network_claim = "not_verified"
        network_reason = f"Route locality is not proven for: {', '.join(uncertain_names)}."
    else:
        network_claim = "not_verified"
        network_reason = "Configured service routes are local; host network isolation is not verified."

    if bridge_ready:
        output_mode = {
            "device": "local_bridge",
            "local_container": "local_bridge",
            "local_network": "local_network_bridge",
            "remote": "remote_bridge",
        }.get(voice_locality, "bridge_unverified")
    else:
        output_mode = "browser_managed_unverified"

    production = mode == "production"
    memory_route = routes.get("database", "unknown") if production else "loopback"
    memory_location = _locality(memory_route) if production else "device"

    return {
        "model": {
            "availability": "ready" if model_ready else "unavailable",
            "name": runtime.get("model"),
            "route": model_route,
            "locality": model_locality,
            "endpoint_available": endpoint_available,
            "installed": model_installed,
            "repair": model_repair(
                str(runtime.get("model") or ""), str(runtime.get("ollama_url") or "").rstrip("/"), backend
            ),
            "reason": (
                "The configured model is available."
                if model_ready
                else "The model endpoint is unavailable."
                if not endpoint_available
                else "The configured model is not listed by the endpoint."
            ),
        },
        "memory": {
            "backend": "postgresql" if production else "jsonl",
            "location": memory_location,
            "conversation_persistence": "enabled",
            "knowledge_tools": "enabled" if runtime.get("tools_enabled", True) else "disabled",
        },
        "voice": {
            "input": "browser_managed_unverified",
            "output": output_mode,
            "bridge_available": bridge_ready,
            "route": voice_route,
        },
        "assets": {"source": "bundled", "remote_dependencies": False},
        "network": {
            "claim": network_claim,
            "routes": routes,
            "reason": network_reason,
            "offline_verified": False,
        },
    }
