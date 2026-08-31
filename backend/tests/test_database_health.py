from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_database_health_check_success():
    with patch("app.main.check_database_connection", return_value=True):
        response = client.get("/api/health/database")
        assert response.status_code == 200
        data = response.json()
        assert data == {
            "status": "ok",
            "database": "connected",
        }


def test_database_health_check_disconnected():
    with patch("app.main.check_database_connection", return_value=False):
        response = client.get("/api/health/database")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "error"
        assert data["detail"]["database"] == "disconnected"


def test_database_health_check_exception():
    with patch("app.main.check_database_connection", side_effect=Exception("DB Error")):
        response = client.get("/api/health/database")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["status"] == "error"
        assert data["detail"]["database"] == "disconnected"
