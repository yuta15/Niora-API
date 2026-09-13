from dataclasses import dataclass

from ..value_objects import WorkspacePresetKey
from ..workspace_definition import WorkspaceDefinition


@dataclass(frozen=True, kw_only=True)
class WorkspacePreset:
    """Nioraが提供するPreset keyとWorkspaceDefinitionの組。"""

    preset_key: WorkspacePresetKey
    definition: WorkspaceDefinition

    def __post_init__(self) -> None:
        if not isinstance(self.preset_key, WorkspacePresetKey):
            raise TypeError("workspace preset key must be a WorkspacePresetKey")
        if not isinstance(self.definition, WorkspaceDefinition):
            raise TypeError("workspace preset definition must be a WorkspaceDefinition")
