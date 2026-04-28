import pytest

from annie.core.config import AnnieConfig, validate_config


def test_default_config_is_valid():
    validate_config(AnnieConfig())


def test_public_config_hides_system_prompt():
    config = AnnieConfig(model="llama3.2")
    data = config.to_public_dict()

    assert data["model"] == "llama3.2"
    assert "system_prompt" not in data


def test_invalid_port_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(port=70000))


def test_invalid_ollama_url_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(ollama_url="localhost:11434"))
