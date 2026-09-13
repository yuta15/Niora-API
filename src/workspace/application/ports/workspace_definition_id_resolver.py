from abc import ABC, abstractmethod
from uuid import UUID

from src.workspace.domain import WorkspacePresetKey


class WorkspaceDefinitionIdResolver(ABC):
    """WorkspacePresetKeyに対応するWorkspaceDefinitionの識別子を解決する。"""

    @abstractmethod
    def resolve(self, preset_key: WorkspacePresetKey) -> UUID | None:
        """対応するDefinition IDを返し、存在しない場合はNoneを返す。"""
