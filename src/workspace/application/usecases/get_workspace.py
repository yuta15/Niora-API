from src.workspace.application import WorkspaceNotFoundError
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
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

        component_outputs: list[WorkspaceComponentOutput] = []
        for component in snapshot.definition.components:
            component_outputs.append(
                WorkspaceComponentOutput(
                    component_key=component.component_key,
                    image=component.image,
                    terminal_exec_available=component.terminal_exec is not None,
                )
            )

        return GetWorkspaceOutput(
            session_id=snapshot.session.id,
            definition_id=snapshot.definition.definition_id,
            expires_at=snapshot.session.expires_at,
            status=snapshot.status,
            components=tuple(component_outputs),
        )
