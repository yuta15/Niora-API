from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.workspace.application.ports import WorkspaceDefinitionIdResolver
from src.workspace.domain import WorkspacePresetKey

from .preset_workspace_definition_mapping_table import PresetWorkspaceDefinitionMappingTable


class SqlAlchemyWorkspaceDefinitionIdResolver(WorkspaceDefinitionIdResolver):
    """SQLAlchemyを使用してPreset KeyからDefinition IDを解決する。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def resolve(self, preset_key: WorkspacePresetKey) -> UUID | None:
        """指定したPreset Keyに対応するDefinition IDを返す。"""
        statement = select(PresetWorkspaceDefinitionMappingTable.definition_id).where(
            PresetWorkspaceDefinitionMappingTable.preset_key == preset_key.value
        )
        return self._session.scalar(statement)
