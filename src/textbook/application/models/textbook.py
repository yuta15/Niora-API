from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class TextbookSummary:
    """教科書一覧に表示する教科書の概要。"""

    id: UUID
    title: str


@dataclass(frozen=True)
class ChapterSummary:
    """教科書に属する章の概要。"""

    id: UUID
    title: str
    position: int


@dataclass(frozen=True)
class ListTextbooksOutput:
    """教科書の一覧。"""

    textbooks: tuple[TextbookSummary, ...]


@dataclass(frozen=True)
class GetTextbookInput:
    """教科書の取得に必要な入力。"""

    textbook_id: UUID


@dataclass(frozen=True)
class GetTextbookOutput:
    """取得した教科書と、その教科書に属する章の一覧。"""

    id: UUID
    title: str
    chapters: tuple[ChapterSummary, ...]
