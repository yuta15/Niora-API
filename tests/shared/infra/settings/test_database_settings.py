from pathlib import Path

from pytest import MonkeyPatch

from src.shared.infra.settings import ApplicationDatabaseSettings, MigrationDatabaseSettings


def test_migration_database_settings_success_create_url_without_application_settings(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Migration用設定だけでMigration Accountの接続URLを構築できることを確認する。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIORA_DATABASE_HOST", "database.example")
    monkeypatch.setenv("NIORA_DATABASE_PORT", "3307")
    monkeypatch.setenv("NIORA_DATABASE_NAME", "niora_test")
    monkeypatch.setenv("NIORA_DATABASE_MIGRATION_USER", "dummy_migration_user")
    monkeypatch.setenv("NIORA_DATABASE_MIGRATION_PASSWORD", "dummy_migration_password")

    settings = MigrationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]

    assert settings.url.drivername == "mysql+pymysql"
    assert settings.url.username == "dummy_migration_user"
    assert settings.url.password == "dummy_migration_password"
    assert settings.url.host == "database.example"
    assert settings.url.port == 3307
    assert settings.url.database == "niora_test"
    assert settings.url.query == {"charset": "utf8mb4"}


def test_application_database_settings_success_create_url_and_pool_settings_without_migration_settings(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """Application用設定だけで接続URLとPool設定を読み込めることを確認する。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("NIORA_DATABASE_HOST", "database.example")
    monkeypatch.setenv("NIORA_DATABASE_PORT", "3307")
    monkeypatch.setenv("NIORA_DATABASE_NAME", "niora_test")
    monkeypatch.setenv("NIORA_DATABASE_APPLICATION_USER", "dummy_application_user")
    monkeypatch.setenv("NIORA_DATABASE_APPLICATION_PASSWORD", "dummy_application_password")
    monkeypatch.setenv("NIORA_DATABASE_POOL_SIZE", "7")
    monkeypatch.setenv("NIORA_DATABASE_MAX_OVERFLOW", "3")
    monkeypatch.setenv("NIORA_DATABASE_POOL_TIMEOUT_SECONDS", "20")
    monkeypatch.setenv("NIORA_DATABASE_POOL_RECYCLE_SECONDS", "900")

    settings = ApplicationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]

    assert settings.url.drivername == "mysql+pymysql"
    assert settings.url.username == "dummy_application_user"
    assert settings.url.password == "dummy_application_password"
    assert settings.url.host == "database.example"
    assert settings.url.port == 3307
    assert settings.url.database == "niora_test"
    assert settings.url.query == {"charset": "utf8mb4"}
    assert settings.pool_size == 7
    assert settings.max_overflow == 3
    assert settings.pool_timeout_seconds == 20
    assert settings.pool_recycle_seconds == 900
