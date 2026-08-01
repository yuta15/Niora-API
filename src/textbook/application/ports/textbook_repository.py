from abc import ABC, abstractmethod
from uuid import UUID

from src.textbook.domain.entities import Textbook


class TextbookRepository(ABC):
    """教科書の永続化先に対する読み取り操作を定義する。"""

    @abstractmethod
    def get(self, textbook_id: UUID) -> Textbook | None:
        """指定した識別子の教科書を返し、存在しない場合はNoneを返す。"""

    @abstractmethod
    def list(self) -> list[Textbook]:
        """すべての教科書を返す。"""
