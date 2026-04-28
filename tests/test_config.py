import pytest

from annie.core.config import AnnieConfig, validate_config


def test_default_config_is_valid():
    validate_config(AnnieConfig())


def test_public_config_hides_system_prompt():
    config = AnnieConfig(model="llama3.2")
    data = config.to_public_dict()

    assert data["model"] == "llama3.2"
    assert "system_prompt" not in data


def test_speed_kernel_config_is_publicly_visible():
    config = AnnieConfig(speed_kernel=True, speed_kernel_backend="dominus-ultra")
    data = config.to_public_dict()

    assert data["speed_kernel"] is True
    assert data["speed_kernel_backend"] == "dominus-ultra"


def test_invalid_port_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(port=70000))


def test_invalid_ollama_url_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(ollama_url="localhost:11434"))


def test_invalid_speed_kernel_backend_rejected():
    with pytest.raises(ValueError):
        validate_config(AnnieConfig(speed_kernel_backend="unknown"))
