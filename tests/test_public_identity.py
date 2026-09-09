import os
import re

from annie.core.config import DEFAULT_DOCTRINE, AnnieConfig
from annie.core.settings import RuntimeSettings, _public_safe_prompt


def test_doctrine_keeps_company_and_state():
    text = DEFAULT_DOCTRINE
    assert "Michigan MindMend Inc." in text
    assert "Michigan nonprofit" in text or "Michigan." in text
    assert re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, flags=re.I) is None
    assert re.search(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text) is None


def test_doctrine_forbids_repeating_origin_copy():
    assert "Do not put origin, company, or maker copy in greetings" in DEFAULT_DOCTRINE
    assert "only if" in DEFAULT_DOCTRINE


def test_guest_settings_hide_doctrine_and_endpoints():
    settings = RuntimeSettings(
        model="llama3.2",
        ollama_url="http://127.0.0.1:11434",
        voice_url="http://127.0.0.1:8123",
        temperature=0.7,
        tools_enabled=True,
        system_prompt=DEFAULT_DOCTRINE,
    )
    guest = settings.to_guest_dict()
    assert "system_prompt" not in guest
    assert "default_doctrine" not in guest
    assert "ollama_url" not in guest
    assert "voice_url" not in guest
    assert guest["demo_lock"] is True
    assert guest["public_attribution"] == "Michigan MindMend Inc."
    assert guest["public_region"] == "Michigan"
    assert guest["tools_enabled"] is False


def test_saved_doctrine_with_blocklisted_place_is_replaced(tmp_path, monkeypatch):
    monkeypatch.setenv("ANNIE_PUBLIC_PLACE_BLOCKLIST", "Exampleville")
    path = tmp_path / "settings.json"
    path.write_text(
        '{"model":"llama3.2","ollama_url":"http://127.0.0.1:11434","voice_url":"http://127.0.0.1:8123","temperature":0.7,"tools_enabled":true,"system_prompt":"Built in Exampleville."}',
        encoding="utf-8",
    )
    loaded = RuntimeSettings.load(path, AnnieConfig())
    assert "Exampleville" not in loaded.system_prompt
    assert "Michigan MindMend Inc." in loaded.system_prompt


def test_email_in_saved_doctrine_is_replaced(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        '{"model":"llama3.2","ollama_url":"http://127.0.0.1:11434","voice_url":"http://127.0.0.1:8123","temperature":0.7,"tools_enabled":true,"system_prompt":"Contact operator@example.com"}',
        encoding="utf-8",
    )
    loaded = RuntimeSettings.load(path, AnnieConfig())
    assert "operator@example.com" not in loaded.system_prompt


def test_ordinary_language_is_kept():
    kept = "Never provide instructions for violence."
    assert _public_safe_prompt(kept, "FALLBACK") == kept
