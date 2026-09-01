from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """指定したEngineへbindした同期Session factoryを生成する。"""
    return sessionmaker(bind=engine)
