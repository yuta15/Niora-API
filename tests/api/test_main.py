from fastapi.testclient import TestClient

from src.api.main import app


def test_app_success_starts_without_external_services() -> None:
    """FastAPIアプリが外部サービスへ接続せず起動できることを確認する。"""
    with TestClient(app) as client:
        response = client.get("/docs")

    assert response.status_code == 200


def test_app_success_exposes_versioned_textbook_routes_in_openapi() -> None:
    """アプリのOpenAPIにv1配下の既存Textbook経路が公開されることを確認する。"""
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/v1/textbooks",
        "/v1/textbooks/{textbook_id}",
        "/v1/textbooks/{textbook_id}/chapters/{chapter_id}",
    }
