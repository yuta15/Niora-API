from dataclasses import dataclass
from uuid import UUID

from src.workspace.domain.entities import WorkspacePresetKey, WorkspaceStatus


@dataclass(frozen=True)
class GetWorkspaceInput:
    """Workspaceの状態取得に必要な入力。"""

    workspace_session_id: UUID


@dataclass(frozen=True)
class GetWorkspaceOutput:
    """取得したWorkspaceのPresetと実行状態。"""

    preset_key: WorkspacePresetKey
    status: WorkspaceStatus
