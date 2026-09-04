from pytest_mock import MockerFixture
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.shared.infra.database import create_session_factory


def test_create_session_factory_success_binds_engine(mocker: MockerFixture) -> None:
    """生成したSession factoryが指定したEngineへbindされることを確認する。"""
    engine = mocker.Mock(spec=Engine)

    session_factory = create_session_factory(engine)
    session = session_factory()

    assert isinstance(session_factory, sessionmaker)
    assert isinstance(session, Session)
    assert session.bind is engine
    session.close()
