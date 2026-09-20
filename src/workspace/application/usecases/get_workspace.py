from src.shared.application.ports import UnitOfWork
from src.workspace.application import WorkspaceNotFoundError
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
from src.workspace.application.ports import Clock, WorkspaceRuntime, WorkspaceSessionRepository


class GetWorkspace:
    """WorkspaceSessionに対応する実行環境の状態を取得する。"""

    def __init__(
        self,
        workspace_session_repository: WorkspaceSessionRepository,
        workspace_runtime: WorkspaceRuntime,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._workspace_session_repository = workspace_session_repository
        self._workspace_runtime = workspace_runtime
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, input: GetWorkspaceInput) -> GetWorkspaceOutput:
        """RuntimeのSnapshotを返し、対象が存在しない場合は例外を送出する。"""
        with self._unit_of_work:
            session = self._workspace_session_repository.get(input.workspace_session_id)

        if session is None or session.is_expired(self._clock.now()):
            raise WorkspaceNotFoundError(input.workspace_session_id)

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
