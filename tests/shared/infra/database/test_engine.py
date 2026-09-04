from pytest_mock import MockerFixture
from sqlalchemy import URL, Engine

from src.shared.infra.database import create_engine
from src.shared.infra.settings import ApplicationDatabaseSettings


def test_create_engine_success_reflects_application_database_settings(mocker: MockerFixture) -> None:
    """Application用設定を同期Engineの接続とPool設定へ反映することを確認する。"""
    settings = mocker.Mock(spec=ApplicationDatabaseSettings)
    settings.url = URL.create(
        drivername="mysql+pymysql",
        username="application_user",
        password="application_password",
        host="database.example",
        port=3306,
        database="niora",
    )
    settings.pool_size = 7
    settings.max_overflow = 3
    settings.pool_timeout_seconds = 20
    settings.pool_recycle_seconds = 900
    expected_engine = mocker.Mock(spec=Engine)
    create_engine_mock = mocker.patch("src.shared.infra.database.engine.sqlalchemy_create_engine")
    create_engine_mock.return_value = expected_engine

    engine = create_engine(settings)

    assert engine is expected_engine
    create_engine_mock.assert_called_once_with(
        settings.url,
        echo=False,
        pool_pre_ping=True,
        pool_size=7,
        max_overflow=3,
        pool_timeout=20,
        pool_recycle=900,
    )
