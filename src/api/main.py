from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.v1.router import router as v1_router
from src.shared.infra.database import create_engine, create_session_factory
from src.shared.infra.settings import ApplicationDatabaseSettings


def create_app(
    database_settings: ApplicationDatabaseSettings | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> FastAPI:
    """Applicationを構成する。Database依存はlifespanまたは明示したfactoryから注入する。"""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine: Engine | None = None
        application_session_factory = session_factory
        if application_session_factory is None:
            settings = database_settings
            if settings is None:
                settings = ApplicationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
            engine = create_engine(settings)
            application_session_factory = create_session_factory(engine)

        application.state.engine = engine
        application.state.session_factory = application_session_factory
        try:
            yield
        finally:
            if engine is not None:
                engine.dispose()

    application = FastAPI(lifespan=lifespan)
    application.include_router(v1_router)
    return application


app = create_app()
