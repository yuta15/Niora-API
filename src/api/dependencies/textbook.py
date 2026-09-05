from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import provide_session
from src.shared.application.ports import UnitOfWork
from src.shared.infra.database import SqlAlchemyUnitOfWork
from src.textbook.application.ports import ChapterRepository, TextbookRepository
from src.textbook.application.usecases import GetChapter, GetTextbook, ListTextbooks
from src.textbook.infra.database import SqlAlchemyChapterRepository, SqlAlchemyTextbookRepository


def provide_textbook_repository(
    session: Annotated[Session, Depends(provide_session)],
) -> TextbookRepository:
    """Textbook Repositoryを提供する。"""
    return SqlAlchemyTextbookRepository(session)


def provide_chapter_repository(
    session: Annotated[Session, Depends(provide_session)],
) -> ChapterRepository:
    """Chapter Repositoryを提供する。"""
    return SqlAlchemyChapterRepository(session)


def provide_unit_of_work(
    session: Annotated[Session, Depends(provide_session)],
) -> UnitOfWork:
    """request単位のSessionを使うUnitOfWorkを提供する。"""
    return SqlAlchemyUnitOfWork(session)


def provide_list_textbooks(
    textbook_repository: Annotated[TextbookRepository, Depends(provide_textbook_repository)],
    unit_of_work: Annotated[UnitOfWork, Depends(provide_unit_of_work)],
) -> ListTextbooks:
    """教科書一覧を取得するUseCaseを提供する。"""
    return ListTextbooks(textbook_repository, unit_of_work)


def provide_get_textbook(
    textbook_repository: Annotated[TextbookRepository, Depends(provide_textbook_repository)],
    chapter_repository: Annotated[ChapterRepository, Depends(provide_chapter_repository)],
    unit_of_work: Annotated[UnitOfWork, Depends(provide_unit_of_work)],
) -> GetTextbook:
    """教科書詳細を取得するUseCaseを提供する。"""
    return GetTextbook(textbook_repository, chapter_repository, unit_of_work)


def provide_get_chapter(
    chapter_repository: Annotated[ChapterRepository, Depends(provide_chapter_repository)],
    unit_of_work: Annotated[UnitOfWork, Depends(provide_unit_of_work)],
) -> GetChapter:
    """章詳細を取得するUseCaseを提供する。"""
    return GetChapter(chapter_repository, unit_of_work)
