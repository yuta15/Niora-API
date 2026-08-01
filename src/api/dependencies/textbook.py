from typing import Annotated

from fastapi import Depends

from src.textbook.application.ports import ChapterRepository, TextbookRepository
from src.textbook.application.usecases import GetChapter, GetTextbook, ListTextbooks


def provide_textbook_repository() -> TextbookRepository:
    """Textbook Repositoryを提供する。"""
    raise RuntimeError("TextbookRepository provider is not configured")


def provide_chapter_repository() -> ChapterRepository:
    """Chapter Repositoryを提供する。"""
    raise RuntimeError("ChapterRepository provider is not configured")


def provide_list_textbooks(
    textbook_repository: Annotated[TextbookRepository, Depends(provide_textbook_repository)],
) -> ListTextbooks:
    """教科書一覧を取得するUseCaseを提供する。"""
    return ListTextbooks(textbook_repository)


def provide_get_textbook(
    textbook_repository: Annotated[TextbookRepository, Depends(provide_textbook_repository)],
    chapter_repository: Annotated[ChapterRepository, Depends(provide_chapter_repository)],
) -> GetTextbook:
    """教科書詳細を取得するUseCaseを提供する。"""
    return GetTextbook(textbook_repository, chapter_repository)


def provide_get_chapter(
    chapter_repository: Annotated[ChapterRepository, Depends(provide_chapter_repository)],
) -> GetChapter:
    """章詳細を取得するUseCaseを提供する。"""
    return GetChapter(chapter_repository)
