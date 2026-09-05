from collections.abc import Generator
from types import SimpleNamespace
from typing import Annotated, Any, cast

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from src.api.dependencies import provide_get_textbook, provide_session
from src.textbook.application.usecases import GetTextbook


class TrackingSession(Session):
    """Session providerのcloseを観測するテスト用Session。"""

    instances: list[TrackingSession] = []

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.close_call_count = 0
        self.instances.append(self)

    def close(self) -> None:
        self.close_call_count += 1
        super().close()


def _session_factory() -> sessionmaker[Session]:
    """Session providerを検証するfactoryを生成する。"""
    return cast(sessionmaker[Session], sessionmaker(class_=TrackingSession))


def _request(session_factory: sessionmaker[Session]) -> Request:
    """Session factoryをApplication stateへ設定したRequest相当値を返す。"""
    return cast(
        Request,
        SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(session_factory=session_factory))),
    )


def test_provide_session_success_closes_session_after_dependency_finishes() -> None:
    """Session providerが正常終了時に生成したSessionをcloseすることを確認する。"""
    TrackingSession.instances = []
    provider = cast(Generator[Session], provide_session(_request(_session_factory())))

    next(provider)
    with pytest.raises(StopIteration):
        next(provider)

    assert TrackingSession.instances[0].close_call_count == 1


def test_provide_session_failure_closes_session_before_propagating_exception() -> None:
    """Session providerが依存処理の例外時にもSessionをcloseすることを確認する。"""
    TrackingSession.instances = []
    provider = cast(Generator[Session], provide_session(_request(_session_factory())))
    next(provider)

    with pytest.raises(RuntimeError, match="request failed"):
        provider.throw(RuntimeError("request failed"))

    assert TrackingSession.instances[0].close_call_count == 1


def test_provide_get_textbook_success_shares_and_closes_one_session() -> None:
    """GetTextbookの両RepositoryとUnitOfWorkが1つのSessionを共有して解放することを確認する。"""
    TrackingSession.instances = []
    application = FastAPI()
    application.state.session_factory = _session_factory()

    @application.get("/")
    def endpoint(use_case: Annotated[GetTextbook, Depends(provide_get_textbook)]) -> dict[str, bool]:
        return {"provided": isinstance(use_case, GetTextbook)}

    with TestClient(application) as client:
        response = client.get("/")

    assert response.json() == {"provided": True}
    assert len(TrackingSession.instances) == 1
    assert TrackingSession.instances[0].close_call_count == 1
