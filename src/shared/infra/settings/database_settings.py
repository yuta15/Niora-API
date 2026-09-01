from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class _DatabaseSettings(BaseSettings):
    """Database接続先の共通設定を提供する。"""

    model_config = SettingsConfigDict(env_prefix="NIORA_DATABASE_", env_file=".env", extra="ignore")

    host: str
    port: int
    name: str

    def _create_url(self, user: SecretStr, password: SecretStr) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=user.get_secret_value(),
            password=password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
            query={"charset": "utf8mb4"},
        )


class MigrationDatabaseSettings(_DatabaseSettings):
    """Schema Migration用Database Accountの設定を提供する。"""

    migration_user: SecretStr
    migration_password: SecretStr

    @property
    def url(self) -> URL:
        return self._create_url(self.migration_user, self.migration_password)


class ApplicationDatabaseSettings(_DatabaseSettings):
    """Application用Database接続とPoolの設定を提供する。"""

    application_user: SecretStr
    application_password: SecretStr
    pool_size: int
    max_overflow: int
    pool_timeout_seconds: int
    pool_recycle_seconds: int

    @property
    def url(self) -> URL:
        return self._create_url(self.application_user, self.application_password)
