from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetChapterInput:
    """章の取得に必要な入力。"""

    textbook_id: UUID
    chapter_id: UUID


@dataclass(frozen=True)
class GetChapterOutput:
    """取得した章の表示内容。"""

    id: UUID
    title: str
    content: str
