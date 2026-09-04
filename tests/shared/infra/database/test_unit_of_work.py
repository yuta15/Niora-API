import pytest
from pytest_mock import MockerFixture
from sqlalchemy.orm import Session

from src.shared.infra.database import SqlAlchemyUnitOfWork


def test_context_manager_success_delegates_commit_to_session(mocker: MockerFixture) -> None:
    """正常終了時にSQLAlchemy Sessionのcommitへ委譲することを確認する。"""
    session = mocker.Mock(spec=Session)

    with SqlAlchemyUnitOfWork(session):
        pass

    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_context_manager_failure_delegates_rollback_to_session(mocker: MockerFixture) -> None:
    """処理中の例外時にSQLAlchemy Sessionのrollbackへ委譲することを確認する。"""
    session = mocker.Mock(spec=Session)

    with pytest.raises(RuntimeError, match="use case failed"):
        with SqlAlchemyUnitOfWork(session):
            raise RuntimeError("use case failed")

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()
