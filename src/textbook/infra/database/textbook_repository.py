from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.textbook.application.ports import TextbookRepository
from src.textbook.domain.entities import Textbook, TitleString

from .textbook_table import TextbookTable


def _create_textbook_entity(table: TextbookTable) -> Textbook:
    """TextbookのTable ModelからDomain Entityを生成する。"""
    return Textbook(id=table.id, title=TitleString(table.title))


class SqlAlchemyTextbookRepository(TextbookRepository):
    """SQLAlchemyを使用してTextbookを読み取るRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, textbook_id: UUID) -> Textbook | None:
        """指定した識別子のTextbookを返す。"""
        table = self._session.get(TextbookTable, textbook_id)
        if table is None:
            return None

        return _create_textbook_entity(table)

    def list(self) -> list[Textbook]:
        """すべてのTextbookを返す。"""
        tables = self._session.scalars(select(TextbookTable)).all()
        return [_create_textbook_entity(table) for table in tables]
