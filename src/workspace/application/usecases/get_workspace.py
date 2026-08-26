from src.workspace.application.exceptions import WorkspaceNotFoundError
from src.workspace.application.models import GetWorkspaceInput, GetWorkspaceOutput
from src.workspace.application.ports import WorkspaceRuntime


class GetWorkspace:
    """WorkspaceSessionに対応する実行環境の状態を取得する。"""

    def __init__(self, workspace_runtime: WorkspaceRuntime) -> None:
        self._workspace_runtime = workspace_runtime

    def execute(self, input: GetWorkspaceInput) -> GetWorkspaceOutput:
        """RuntimeのSnapshotを返し、対象が存在しない場合は例外を送出する。"""
        snapshot = self._workspace_runtime.find(input.workspace_session_id)
        if snapshot is None:
            raise WorkspaceNotFoundError(input.workspace_session_id)

        return GetWorkspaceOutput(
            preset_key=snapshot.preset_key,
            status=snapshot.status,
        )
