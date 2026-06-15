from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fastapi_app.main import app


@pytest.mark.django_db
def test_fastapi_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.django_db
def test_fastapi_bot_status_creates_safe_default_state() -> None:
    client = TestClient(app)

    response = client.get("/bot/status")

    assert response.status_code == 200
    assert response.json()["is_running"] is False
    assert response.json()["kill_switch_active"] is False
