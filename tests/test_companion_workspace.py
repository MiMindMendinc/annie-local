from __future__ import annotations

from dataclasses import replace
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from annie.core.llm import ModelTurn
from annie.env import get_settings
from annie.server import create_app


@pytest.mark.parametrize(
    "kind,collection", [("profile", "profile"), ("fact", "facts"), ("goal", "goals"), ("journal", "journal")]
)
def test_capture_without_model_persists_after_restart(api_client, kind, collection):
    with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
        assert api_client.get("/api/knowledge").status_code == 200  # populate the cache
        response = api_client.post("/api/knowledge", json={"kind": kind, "text": "  Keep this useful detail  "})
        assert response.status_code == 201
        current = api_client.get("/api/knowledge").json()
        model.assert_not_called()
    with TestClient(create_app(api_client.app.state.annie.config)) as restarted:
        assert restarted.get("/api/knowledge").json() == current
    if kind == "profile":
        assert current[collection] == "Keep this useful detail"
    else:
        assert len(current[collection]) == 1
        assert current[collection][0]["entry" if kind == "journal" else "text"] == "Keep this useful detail"


def test_goal_completion_targets_id_is_idempotent_and_reversible(api_client):
    first = api_client.post("/api/knowledge", json={"kind": "goal", "text": "Ship the demo"}).json()["id"]
    second = api_client.post("/api/knowledge", json={"kind": "goal", "text": "Ship the demo"}).json()["id"]
    api_client.get("/api/knowledge")
    path = f"/api/knowledge/goals/{second}"
    for _ in range(2):
        result = api_client.patch(path, json={"done": True})
        assert result.status_code == 200
        assert result.json()["done"] is True
    goals = {goal["id"]: goal["done"] for goal in api_client.get("/api/knowledge").json()["goals"]}
    assert goals == {first: False, second: True}
    assert api_client.patch(path, json={"done": False}).json()["done"] is False
    assert not any(goal["done"] for goal in api_client.get("/api/knowledge").json()["goals"])
    assert api_client.patch("/api/knowledge/goals/missing", json={"done": True}).status_code == 404
    assert api_client.patch(path, json={}).status_code == 422
    assert api_client.patch(path, json={"done": "yes"}).status_code == 422


@pytest.mark.parametrize(
    "payload,status",
    [
        ({"kind": "unknown", "text": "hello"}, 422),
        ({"kind": "fact", "text": ""}, 422),
        ({"kind": "fact", "text": "   "}, 400),
        ({"kind": "fact", "text": "<b></b>"}, 400),
        ({"kind": "fact", "text": "x" * 4001}, 422),
    ],
)
def test_invalid_capture_does_not_mutate_memory(api_client, payload, status):
    before = api_client.get("/api/knowledge").json()
    assert api_client.post("/api/knowledge", json=payload).status_code == status
    assert api_client.get("/api/knowledge").json() == before


def test_profile_notes_append_and_feed_future_conversations(api_client):
    for note in ("Call me Alex.", "I like short checklists."):
        assert api_client.post("/api/knowledge", json={"kind": "profile", "text": note}).status_code == 201
    with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
        model.return_value = ModelTurn(content="Here is a small next step.")
        assert api_client.post("/api/chat", json={"message": "Help me plan."}).status_code == 200
        context = model.call_args.args[0][0].content
    assert "Call me Alex.\nI like short checklists." in context


def test_manual_capture_still_works_with_knowledge_tools_disabled(api_client):
    assert api_client.put("/api/settings", json={"tools_enabled": False}).status_code == 200
    assert (
        api_client.post("/api/knowledge", json={"kind": "fact", "text": "A unique private preference"}).status_code
        == 201
    )
    with patch("annie.core.llm.OllamaBackend.chat", new_callable=AsyncMock) as model:
        model.return_value = ModelTurn(content="Hello.")
        assert api_client.post("/api/chat", json={"message": "Hi."}).status_code == 200
        assert "A unique private preference" not in model.call_args.args[0][0].content
        assert model.call_args.kwargs["tools"] is None


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("POST", "/api/knowledge", {"kind": "goal", "text": "A goal"}),
        ("PATCH", "/api/knowledge/goals/any-id", {"done": True}),
    ],
)
def test_workspace_writes_require_auth_when_enabled(api_client, method, path, payload):
    protected = replace(get_settings(), auth_disabled=False)
    before = api_client.get("/api/knowledge").json()
    with patch("annie.api.deps.auth.get_settings", return_value=protected):
        assert api_client.request(method, path, json=payload).status_code == 401
        assert (
            api_client.request(method, path, json=payload, headers={"Authorization": "Bearer invalid"}).status_code
            == 401
        )
    assert api_client.get("/api/knowledge").json() == before


def test_workspace_assets_are_packaged_and_served(api_client):
    html = api_client.get("/").text
    for name in ("companion.css", "companion.js"):
        path = f"/static/{name}"
        assert path in html
        assert api_client.get(path).status_code == 200


def test_goal_update_preflight_respects_configured_origins(api_client):
    for origin, expected in [(get_settings().cors_origins[0], 200), ("https://untrusted.invalid", 400)]:
        response = api_client.options(
            "/api/knowledge/goals/test-goal",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == expected
