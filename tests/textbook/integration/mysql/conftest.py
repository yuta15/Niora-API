import os
import secrets
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL, Engine
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.main import create_app
from src.shared.infra.database import create_engine, create_session_factory
from src.shared.infra.settings import ApplicationDatabaseSettings, MigrationDatabaseSettings

_PROJECT_ROOT = Path(__file__).parents[4]


class _AdminDatabaseSettings(BaseSettings):
    """IntegrationテストのDatabase管理Account設定を読み込む。"""

    model_config = SettingsConfigDict(env_prefix="NIORA_DATABASE_", env_file=".env", extra="ignore")

    admin_password: SecretStr


def _create_database_resources(
    admin_engine: Engine,
    database_name: str,
    migration_user: str,
    migration_password: str,
    application_user: str,
    application_password: str,
) -> None:
    """テスト専用Databaseと最小権限のAccountを作成する。"""
    with admin_engine.begin() as connection:
        connection.exec_driver_sql(
            f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
        connection.exec_driver_sql(
            "CREATE USER %s@'%%' IDENTIFIED BY %s",
            (migration_user, migration_password),
        )
        connection.exec_driver_sql(
            f"GRANT ALL PRIVILEGES ON `{database_name}`.* TO %s@'%%'",
            (migration_user,),
        )
        connection.exec_driver_sql(
            "CREATE USER %s@'%%' IDENTIFIED BY %s",
            (application_user, application_password),
        )
        connection.exec_driver_sql(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON `{database_name}`.* TO %s@'%%'",
            (application_user,),
        )


def _run_migrations(settings: MigrationDatabaseSettings, working_directory: Path) -> None:
    """テスト専用DatabaseへAlembic Migrationを適用する。"""
    migration_environment = os.environ.copy()
    migration_environment.update(
        {
            "NIORA_DATABASE_HOST": settings.host,
            "NIORA_DATABASE_PORT": str(settings.port),
            "NIORA_DATABASE_NAME": settings.name,
            "NIORA_DATABASE_MIGRATION_USER": settings.migration_user.get_secret_value(),
            "NIORA_DATABASE_MIGRATION_PASSWORD": settings.migration_password.get_secret_value(),
            "PYTHONPATH": str(_PROJECT_ROOT),
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(_PROJECT_ROOT / "alembic.ini"), "upgrade", "head"],
        cwd=working_directory,
        env=migration_environment,
        check=True,
    )


def _drop_database_resources(
    admin_engine: Engine,
    database_name: str,
    migration_user: str,
    application_user: str,
) -> list[BaseException]:
    """テスト専用DatabaseとAccountを削除する。"""
    cleanup_errors: list[BaseException] = []

    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS `{database_name}`")
    except BaseException as error:
        cleanup_errors.append(error)

    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql("DROP USER IF EXISTS %s@'%%'", (migration_user,))
    except BaseException as error:
        cleanup_errors.append(error)

    try:
        with admin_engine.begin() as connection:
            connection.exec_driver_sql("DROP USER IF EXISTS %s@'%%'", (application_user,))
    except BaseException as error:
        cleanup_errors.append(error)

    return cleanup_errors


def _cleanup_database_resources(
    admin_engine: Engine,
    application_engine: Engine | None,
    database_name: str,
    migration_user: str,
    application_user: str,
) -> list[BaseException]:
    """すべてのテスト用Databaseリソースの後始末を試行する。"""
    cleanup_errors: list[BaseException] = []

    if application_engine is not None:
        try:
            application_engine.dispose()
        except BaseException as error:
            cleanup_errors.append(error)

    try:
        cleanup_errors.extend(
            _drop_database_resources(
                admin_engine,
                database_name,
                migration_user,
                application_user,
            )
        )
    except BaseException as error:
        cleanup_errors.append(error)

    try:
        admin_engine.dispose()
    except BaseException as error:
        cleanup_errors.append(error)

    return cleanup_errors


@pytest.fixture
def mysql_session(tmp_path: Path) -> Iterator[Session]:
    """Migration適用済みのテスト専用Databaseへ接続するSessionを提供する。"""
    database_suffix = uuid4().hex
    database_name = f"niora_test_{database_suffix}"
    migration_user = f"niora_m_{database_suffix[:16]}"
    application_user = f"niora_a_{database_suffix[:16]}"
    migration_password = secrets.token_urlsafe(32)
    application_password = secrets.token_urlsafe(32)

    base_migration_settings = MigrationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
    base_application_settings = ApplicationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
    admin_settings = _AdminDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]

    migration_settings = base_migration_settings.model_copy(
        update={
            "name": database_name,
            "migration_user": SecretStr(migration_user),
            "migration_password": SecretStr(migration_password),
        }
    )
    application_settings = base_application_settings.model_copy(
        update={
            "name": database_name,
            "application_user": SecretStr(application_user),
            "application_password": SecretStr(application_password),
        }
    )
    admin_url = URL.create(
        drivername="mysql+pymysql",
        username="root",
        password=admin_settings.admin_password.get_secret_value(),
        host=migration_settings.host,
        port=migration_settings.port,
        query={"charset": "utf8mb4"},
    )
    admin_engine = sqlalchemy_create_engine(admin_url, echo=False, hide_parameters=True, pool_pre_ping=True)
    application_engine: Engine | None = None

    try:
        _create_database_resources(
            admin_engine,
            database_name,
            migration_user,
            migration_password,
            application_user,
            application_password,
        )
        _run_migrations(migration_settings, tmp_path)
        application_engine = create_engine(application_settings)
        session_factory = create_session_factory(application_engine)
        with session_factory() as session:
            yield session
    except BaseException as original_error:
        cleanup_errors = _cleanup_database_resources(
            admin_engine,
            application_engine,
            database_name,
            migration_user,
            application_user,
        )
        if cleanup_errors:
            raise BaseExceptionGroup(
                "IntegrationテストとDatabaseリソースの後始末に失敗しました",
                [original_error, *cleanup_errors],
            ) from None
        raise
    else:
        cleanup_errors = _cleanup_database_resources(
            admin_engine,
            application_engine,
            database_name,
            migration_user,
            application_user,
        )
        if cleanup_errors:
            raise BaseExceptionGroup(
                "Databaseリソースの後始末に失敗しました",
                cleanup_errors,
            )


@pytest.fixture
def mysql_api_client(mysql_session: Session) -> Iterator[TestClient]:
    """テストデータ用Sessionとは分離したSession factoryでAPI Clientを提供する。"""
    engine = cast(Engine, mysql_session.get_bind())
    api_sessions: list[Session] = []

    class TrackingSession(Session):
        """実MySQLへ接続したAPI Sessionのcloseを記録する。"""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.close_call_count = 0
            api_sessions.append(self)

        def close(self) -> None:
            self.close_call_count += 1
            super().close()

    session_factory = cast(sessionmaker[Session], sessionmaker(bind=engine, class_=TrackingSession))
    with TestClient(create_app(session_factory=session_factory)) as client:
        yield client

    for session in api_sessions:
        assert isinstance(session, TrackingSession)
        assert session.close_call_count == 1
