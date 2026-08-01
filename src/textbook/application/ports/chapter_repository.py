from abc import ABC, abstractmethod
from uuid import UUID

from src.textbook.domain.entities.chapter import Chapter


class ChapterRepository(ABC):
    """章の永続化先に対する読み取り操作を定義する。"""

    @abstractmethod
    def get(self, chapter_id: UUID) -> Chapter | None:
        """指定した識別子の章を返し、存在しない場合はNoneを返す。"""

    @abstractmethod
    def list(self, textbook_id: UUID) -> list[Chapter]:
        """指定した教科書に属する章を位置の昇順で返す。"""
