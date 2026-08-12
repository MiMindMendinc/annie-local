from __future__ import annotations

from html.parser import HTMLParser
from importlib.resources import files


class UiParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: dict[str, tuple[str, dict[str, str | None]]] = {}
        self.external_assets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        element_id = values.get("id")
        if element_id:
            self.elements[element_id] = (tag, values)
        for name in ("src", "href"):
            value = values.get(name) or ""
            if value.startswith(("http://", "https://", "//")):
                self.external_assets.append(value)


def _ui_text(name: str) -> str:
    return files("annie").joinpath("ui", name).read_text(encoding="utf-8")


def test_research_session_controls_are_accessible_and_local() -> None:
    html = _ui_text("index.html")
    parser = UiParser()
    parser.feed(html)

    required_buttons = {
        "menuBtn",
        "stopBtn",
        "modelBtn",
        "exportBtn",
        "cfgBtn",
        "attachBtn",
        "mic",
        "send",
    }
    for element_id in required_buttons:
        tag, attrs = parser.elements[element_id]
        assert tag == "button"
        assert attrs.get("aria-label")

    assert parser.elements["voicePill"][1].get("role") == "status"
    assert parser.elements["voicePill"][1].get("aria-live") == "polite"
    assert parser.elements["input"][0] == "textarea"
    assert parser.external_assets == []


def test_ui_does_not_hardcode_unverified_privacy_claims() -> None:
    html = _ui_text("index.html").lower()
    for forbidden in ("air-gapped", "fully offline", "no wire out", "network: offline"):
        assert forbidden not in html
    assert "network: not verified" in html
    assert "knowledge tools" in html
    assert "conversation persistence is separate" in html


def test_motion_and_phase_contracts_are_present() -> None:
    css = _ui_text("styles.css")
    state = _ui_text("state.js")
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ":focus-visible" in css
    assert "min-height: 44px" in css
    for phase in ("idle", "listening", "thinking", "speaking", "offline", "error"):
        assert f'"{phase}"' in state


def test_production_sign_in_is_accessible_and_session_scoped() -> None:
    parser = UiParser()
    parser.feed(_ui_text("index.html"))
    assert parser.elements["authDialog"][0] == "dialog"
    assert parser.elements["authDialog"][1].get("aria-labelledby") == "authTitle"
    assert parser.elements["authForm"][0] == "form"
    assert parser.elements["authEmail"][1].get("autocomplete") == "username"
    assert parser.elements["authPassword"][1].get("autocomplete") == "current-password"
    assert parser.elements["authError"][1].get("role") == "alert"

    state = _ui_text("state.js")
    api_client = _ui_text("api-client.js")
    assert "global.sessionStorage" in state
    assert 'sessionStore.get("auth.token"' in state
    assert 'storage.get("auth.token"' not in state
    assert 'CustomEvent("annie:auth-required"' in api_client
