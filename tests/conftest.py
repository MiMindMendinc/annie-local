from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from annie.core.config import AnnieConfig
from annie.server import create_app


@pytest.fixture
def api_client(tmp_path):
    config = AnnieConfig(
        memory_path=str(tmp_path / "memory.jsonl"),
        knowledge_path=str(tmp_path / "knowledge.json"),
        settings_path=str(tmp_path / "settings.json"),
    )
    with TestClient(create_app(config), base_url="http://127.0.0.1:8787") as client:
        yield client
