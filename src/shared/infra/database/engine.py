from sqlalchemy import Engine
from sqlalchemy import create_engine as sqlalchemy_create_engine

from src.shared.infra.settings import ApplicationDatabaseSettings


def create_engine(settings: ApplicationDatabaseSettings) -> Engine:
    """Application用設定から同期SQLAlchemy Engineを生成する。"""
    return sqlalchemy_create_engine(
        settings.url,
        echo=False,
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout_seconds,
        pool_recycle=settings.pool_recycle_seconds,
    )
