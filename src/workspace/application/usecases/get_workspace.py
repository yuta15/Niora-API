from src.shared.application.ports import UnitOfWork
from src.workspace.application import WorkspaceNotFoundError, WorkspaceSessionDefinitionNotFoundError
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
from src.workspace.application.ports import (
    Clock,
    WorkspaceDefinitionRepository,
    WorkspaceRuntime,
    WorkspaceSessionRepository,
)
from src.workspace.domain import WorkspaceStatus


class GetWorkspace:
    """WorkspaceSessionに対応する実行環境の状態を取得する。"""

    def __init__(
        self,
        workspace_session_repository: WorkspaceSessionRepository,
        workspace_definition_repository: WorkspaceDefinitionRepository,
        workspace_runtime: WorkspaceRuntime,
        unit_of_work: UnitOfWork,
        clock: Clock,
    ) -> None:
        self._workspace_session_repository = workspace_session_repository
        self._workspace_definition_repository = workspace_definition_repository
        self._workspace_runtime = workspace_runtime
        self._unit_of_work = unit_of_work
        self._clock = clock

    def execute(self, input: GetWorkspaceInput) -> GetWorkspaceOutput:
        """SessionとDefinitionの情報、およびRuntimeの実行状態を返す。"""
        now = self._clock.now()
        with self._unit_of_work:
            session = self._workspace_session_repository.get(input.workspace_session_id)
            definition = None
            if session is not None and not session.is_expired(now):
                definition = self._workspace_definition_repository.get(session.definition_id)

        if session is None or session.is_expired(now):
            raise WorkspaceNotFoundError(input.workspace_session_id)

        if definition is None:
            raise WorkspaceSessionDefinitionNotFoundError(session.definition_id)

        snapshot = self._workspace_runtime.find(input.workspace_session_id)

        component_outputs: list[WorkspaceComponentOutput] = []
        for component in definition.components:
            component_outputs.append(
                WorkspaceComponentOutput(
                    component_key=component.component_key,
                    image=component.image,
                    terminal_exec_available=component.terminal_exec is not None,
                )
            )

        return GetWorkspaceOutput(
            session_id=session.id,
            definition_id=definition.definition_id,
            expires_at=session.expires_at,
            status=WorkspaceStatus.MISSING if snapshot is None else snapshot.status,
            components=tuple(component_outputs),
        )
