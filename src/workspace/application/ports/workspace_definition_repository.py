from abc import ABC, abstractmethod
from uuid import UUID

from src.workspace.domain import WorkspaceDefinition


class WorkspaceDefinitionRepository(ABC):
    """WorkspaceDefinitionの永続化先に対する読み取り操作を定義する。"""

    @abstractmethod
    def get(self, definition_id: UUID) -> WorkspaceDefinition | None:
        """指定した識別子のDefinitionを返し、存在しない場合はNoneを返す。"""
