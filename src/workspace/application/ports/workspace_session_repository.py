from abc import ABC, abstractmethod
from uuid import UUID

from src.workspace.domain import WorkspaceSession


class WorkspaceSessionRepository(ABC):
    """WorkspaceSessionの永続化先に対する操作を定義する。"""

    @abstractmethod
    def get(self, id: UUID) -> WorkspaceSession | None:
        """指定した識別子のWorkspaceSessionを返す。"""

    @abstractmethod
    def add(self, session: WorkspaceSession) -> None:
        """WorkspaceSessionを追加する。"""

    @abstractmethod
    def delete(self, id: UUID) -> None:
        """指定した識別子のWorkspaceSessionを削除する。"""
