from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from src.workspace.domain.entities import WorkspacePresetKey, WorkspaceSession, WorkspaceStatus


@dataclass(frozen=True)
class WorkspaceRuntimeSnapshot:
    """Runtimeが観測したWorkspaceのPresetと実行状態。"""

    preset_key: WorkspacePresetKey
    status: WorkspaceStatus


class WorkspaceRuntime(ABC):
    """WorkspaceSessionに対応する実行環境を操作する。"""

    @abstractmethod
    def create(self, session: WorkspaceSession) -> None:
        """実行環境の作成要求を完了し、Ready状態になるまでは待機しない。"""

    @abstractmethod
    def delete(self, workspace_session_id: UUID) -> None:
        """必要な削除要求を受理するまで待機し、対象が存在しない場合も成功とする。"""

    @abstractmethod
    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        """WorkspaceのSnapshotを返し、対象が存在しない場合はNoneを返す。"""
