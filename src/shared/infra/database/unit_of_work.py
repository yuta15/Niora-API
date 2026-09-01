from sqlalchemy.orm import Session

from src.shared.application.ports import UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """注入されたSQLAlchemy SessionへTransaction操作を委譲する。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def _commit(self) -> None:
        """注入されたSessionのTransactionをcommitする。"""
        self._session.commit()

    def _rollback(self) -> None:
        """注入されたSessionのTransactionをrollbackする。"""
        self._session.rollback()
