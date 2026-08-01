from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from src.textbook.domain.entities import Chapter


class ChapterRepository(ABC):
    """章の永続化先に対する読み取り操作を定義する。"""

    @abstractmethod
    def get(self, textbook_id: UUID, chapter_id: UUID) -> Chapter | None:
        """指定した教科書に属する章を返し、存在しない場合はNoneを返す。"""

    @abstractmethod
    def list(self, textbook_id: UUID) -> Sequence[Chapter]:
        """指定した教科書に属する章を位置の昇順で返す。"""
