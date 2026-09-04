from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.textbook.application.ports import ChapterRepository
from src.textbook.domain.entities import Chapter, ChapterPosition, ContentString, TitleString

from .chapter_table import ChapterTable


def _create_chapter_entity(table: ChapterTable) -> Chapter:
    """ChapterのTable ModelからDomain Entityを生成する。"""
    return Chapter(
        id=table.id,
        textbook_id=table.textbook_id,
        position=ChapterPosition(table.position),
        title=TitleString(table.title),
        content=ContentString(table.content),
        workspace_preset_key=table.workspace_preset_key,
    )


class SqlAlchemyChapterRepository(ChapterRepository):
    """SQLAlchemyを使用してChapterを読み取るRepository。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, textbook_id: UUID, chapter_id: UUID) -> Chapter | None:
        """指定したTextbookに属するChapterを返す。"""
        statement = select(ChapterTable).where(
            ChapterTable.textbook_id == textbook_id,
            ChapterTable.id == chapter_id,
        )
        table = self._session.scalar(statement)
        if table is None:
            return None

        return _create_chapter_entity(table)

    def list(self, textbook_id: UUID) -> Sequence[Chapter]:
        """指定したTextbookに属するChapterをpositionの昇順で返す。"""
        statement = (
            select(ChapterTable).where(ChapterTable.textbook_id == textbook_id).order_by(ChapterTable.position.asc())
        )
        tables = self._session.scalars(statement).all()
        return [_create_chapter_entity(table) for table in tables]
