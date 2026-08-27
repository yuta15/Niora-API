from abc import ABC, abstractmethod
from uuid import UUID


class WorkspaceSessionIdGenerator(ABC):
    """WorkspaceSessionの識別子を生成する。"""

    @abstractmethod
    def generate(self) -> UUID:
        """新しいWorkspaceSessionの識別子を返す。"""
