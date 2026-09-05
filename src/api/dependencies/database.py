from collections.abc import Callable, Iterator
from typing import cast

from fastapi import Request
from sqlalchemy.orm import Session


def provide_session(request: Request) -> Iterator[Session]:
    """ApplicationのSession factoryからrequest単位のSessionを提供する。"""
    session_factory = getattr(request.app.state, "session_factory", None)
    if not callable(session_factory):
        raise RuntimeError("Database session factory is not configured")

    session = cast(Callable[[], Session], session_factory)()
    try:
        yield session
    finally:
        session.close()
