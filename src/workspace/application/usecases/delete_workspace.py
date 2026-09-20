from src.shared.application.ports import UnitOfWork
from src.workspace.application.models import DeleteWorkspaceInput
from src.workspace.application.ports import Clock, WorkspaceRuntime, WorkspaceSessionRepository


class DeleteWorkspace:
    """WorkspaceSessionに対応する実行環境の削除を要求する。"""

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

    def execute(self, input: DeleteWorkspaceInput) -> None:
        """Sessionの存在を確認してからRuntimeと永続化先を削除する。"""
        with self._unit_of_work:
            session = self._workspace_session_repository.get(input.workspace_session_id)

        if session is None or session.is_expired(self._clock.now()):
            return

        self._workspace_runtime.delete(input.workspace_session_id)

        with self._unit_of_work:
            self._workspace_session_repository.delete(input.workspace_session_id)
