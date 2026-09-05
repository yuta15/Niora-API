from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.main import create_app
from src.shared.infra.settings import ApplicationDatabaseSettings


def test_app_success_starts_without_external_services() -> None:
    """FastAPIアプリが外部サービスへ接続せず起動できることを確認する。"""
    with TestClient(create_app(session_factory=sessionmaker(class_=Session))) as client:
        response = client.get("/docs")

    assert response.status_code == 200


def test_app_success_exposes_versioned_textbook_routes_in_openapi() -> None:
    """アプリのOpenAPIにv1配下の既存Textbook経路が公開されることを確認する。"""
    with TestClient(create_app(session_factory=sessionmaker(class_=Session))) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/v1/textbooks",
        "/v1/textbooks/{textbook_id}",
        "/v1/textbooks/{textbook_id}/chapters/{chapter_id}",
    }


def test_create_app_success_disposes_database_engine_on_shutdown(mocker: MockerFixture) -> None:
    """lifespanがDatabase EngineとSession factoryを構成し終了時にEngineをdisposeすることを確認する。"""
    settings = mocker.Mock(spec=ApplicationDatabaseSettings)
    engine = mocker.Mock(spec=Engine)
    create_engine_mock = mocker.patch("src.api.main.create_engine", return_value=engine)

    with TestClient(create_app(database_settings=settings)) as client:
        assert client.get("/docs").status_code == 200

    create_engine_mock.assert_called_once_with(settings)
    engine.dispose.assert_called_once_with()
