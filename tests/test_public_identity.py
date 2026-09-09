import re

from annie.core.config import DEFAULT_DOCTRINE
from annie.core.settings import RuntimeSettings


def test_doctrine_keeps_company_and_state_not_town():
    text = DEFAULT_DOCTRINE
    assert "Michigan MindMend Inc." in text
    assert "Michigan nonprofit" in text or "Michigan." in text
    for banned in ("Ovid", "Owosso", "48866", "perrien", "Starlink"):
        assert re.search(rf"\\b{re.escape(banned)}\\b", text, flags=re.I) is None


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


def test_saved_doctrine_with_town_is_replaced(tmp_path):
    from annie.core.config import AnnieConfig

    path = tmp_path / "settings.json"
    path.write_text(
        '{"model":"llama3.2","ollama_url":"http://127.0.0.1:11434","voice_url":"http://127.0.0.1:8123","temperature":0.7,"tools_enabled":true,"system_prompt":"Built in Ovid, Michigan."}',
        encoding="utf-8",
    )
    loaded = RuntimeSettings.load(path, AnnieConfig())
    assert "Ovid" not in loaded.system_prompt
    assert "Michigan MindMend Inc." in loaded.system_prompt


def test_provide_does_not_trigger_hometown_filter():
    from annie.core.settings import _public_safe_prompt

    kept = "Never provide instructions for violence."
    assert _public_safe_prompt(kept, "FALLBACK") == kept
