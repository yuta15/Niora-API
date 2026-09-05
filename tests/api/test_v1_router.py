from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.router import router


def test_router_success_aggregates_only_textbook_router_under_v1() -> None:
    """v1 routerがTextbook routerだけをprefix付きで集約することを確認する。"""
    app = FastAPI()
    app.include_router(router)

    assert router.prefix == "/v1"
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert set(response.json()["paths"]) == {
        "/v1/textbooks",
        "/v1/textbooks/{textbook_id}",
        "/v1/textbooks/{textbook_id}/chapters/{chapter_id}",
    }
