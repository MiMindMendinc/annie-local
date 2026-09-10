import json
import re

from annie.core.config import DEFAULT_DOCTRINE, AnnieConfig
from annie.core.settings import RuntimeSettings


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


def test_local_saved_doctrine_is_not_silently_rewritten(tmp_path):
    prompt = "Provide context about Exampleville. Contact operator@example.com or 202-555-0100."
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"system_prompt": prompt}), encoding="utf-8")
    loaded = RuntimeSettings.load(path, AnnieConfig())
    assert loaded.system_prompt == prompt
    assert json.loads(path.read_text())["system_prompt"] == prompt
