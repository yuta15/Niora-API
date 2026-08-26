from src.workspace.application.models import DeleteWorkspaceInput
from src.workspace.application.ports import WorkspaceRuntime


class DeleteWorkspace:
    """WorkspaceSessionに対応する実行環境の削除を要求する。"""

    def __init__(self, workspace_runtime: WorkspaceRuntime) -> None:
        self._workspace_runtime = workspace_runtime

    def execute(self, input: DeleteWorkspaceInput) -> None:
        """必要な削除要求が受理されるまでRuntimeへ処理を委譲する。"""
        self._workspace_runtime.delete(input.workspace_session_id)
