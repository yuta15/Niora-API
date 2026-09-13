from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.workspace.domain.entities import WorkspaceStatus


@dataclass(frozen=True)
class GetWorkspaceInput:
    """Workspaceの状態取得に必要な入力。"""

    workspace_session_id: UUID


@dataclass(frozen=True)
class WorkspaceComponentOutput:
    """WorkspaceDefinitionを構成するComponentの表示内容。"""

    component_key: str
    image: str
    terminal_exec_available: bool


@dataclass(frozen=True)
class GetWorkspaceOutput:
    """取得したWorkspaceSession、Definitionの構成、および実行状態。"""

    session_id: UUID
    definition_id: UUID
    expires_at: datetime
    status: WorkspaceStatus
    components: tuple[WorkspaceComponentOutput, ...]
