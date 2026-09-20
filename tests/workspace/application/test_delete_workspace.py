from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.shared.application.ports import UnitOfWork
from src.workspace.application.models import DeleteWorkspaceInput
from src.workspace.application.ports import (
    Clock,
    WorkspaceRuntime,
    WorkspaceRuntimeSnapshot,
    WorkspaceSessionRepository,
)
from src.workspace.application.usecases import DeleteWorkspace
from src.workspace.domain import WorkspaceDefinition, WorkspaceSession

WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
WORKSPACE_DEFINITION_ID = UUID("dd1c64fa-8763-4f06-aa92-929d08d04dd0")
NOW = datetime(2026, 9, 14, tzinfo=UTC)


class FakeWorkspaceSessionRepository(WorkspaceSessionRepository):
    def __init__(self, session: WorkspaceSession | None) -> None:
        self._session = session
        self.received_get_ids: list[UUID] = []
        self.deleted_ids: list[UUID] = []

    def get(self, id: UUID) -> WorkspaceSession | None:
        self.received_get_ids.append(id)
        return self._session

    def add(self, session: WorkspaceSession) -> None:
        raise AssertionError(f"unexpected workspace session addition: {session.id}")

    def delete(self, id: UUID) -> None:
        self.deleted_ids.append(id)


class FakeWorkspaceRuntime(WorkspaceRuntime):
    def __init__(self, delete_error: Exception | None = None) -> None:
        self._delete_error = delete_error
        self.deleted_ids: list[UUID] = []

    def create(self, session: WorkspaceSession, definition: WorkspaceDefinition) -> None:
        raise AssertionError(f"unexpected workspace creation: {session.id}")

    def delete(self, workspace_session_id: UUID) -> None:
        self.deleted_ids.append(workspace_session_id)
        if self._delete_error is not None:
            raise self._delete_error

    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        raise AssertionError(f"unexpected workspace lookup: {workspace_session_id}")


class SpyUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commit_call_count = 0
        self.rollback_call_count = 0

    def _commit(self) -> None:
        self.commit_call_count += 1

    def _rollback(self) -> None:
        self.rollback_call_count += 1


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


def _session(expires_at: datetime = NOW + timedelta(hours=1)) -> WorkspaceSession:
    return WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=expires_at,
    )


def test_execute_success_deletes_runtime_before_persisted_session() -> None:
    """存在するSessionはRuntime削除成功後に永続化先から削除する。"""
    repository = FakeWorkspaceSessionRepository(_session())
    runtime = FakeWorkspaceRuntime()
    unit_of_work = SpyUnitOfWork()

    DeleteWorkspace(repository, runtime, unit_of_work, FixedClock()).execute(
        DeleteWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID)
    )

    assert repository.received_get_ids == [WORKSPACE_SESSION_ID]
    assert runtime.deleted_ids == [WORKSPACE_SESSION_ID]
    assert repository.deleted_ids == [WORKSPACE_SESSION_ID]
    assert unit_of_work.commit_call_count == 2
    assert unit_of_work.rollback_call_count == 0


def test_execute_success_when_session_does_not_exist_does_not_call_runtime() -> None:
    """SessionがないDeleteは完了とし、Runtimeと削除transactionを呼ばない。"""
    repository = FakeWorkspaceSessionRepository(None)
    runtime = FakeWorkspaceRuntime()
    unit_of_work = SpyUnitOfWork()

    DeleteWorkspace(repository, runtime, unit_of_work, FixedClock()).execute(
        DeleteWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID)
    )

    assert runtime.deleted_ids == []
    assert repository.deleted_ids == []
    assert unit_of_work.commit_call_count == 1


def test_execute_failure_keeps_persisted_session_when_runtime_deletion_fails() -> None:
    """Runtime削除が失敗した場合は永続化先のSessionを維持する。"""
    repository = FakeWorkspaceSessionRepository(_session())
    runtime = FakeWorkspaceRuntime(delete_error=RuntimeError("runtime deletion failed"))
    unit_of_work = SpyUnitOfWork()

    with pytest.raises(RuntimeError, match="runtime deletion failed"):
        DeleteWorkspace(repository, runtime, unit_of_work, FixedClock()).execute(
            DeleteWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID)
        )

    assert repository.deleted_ids == []
    assert unit_of_work.commit_call_count == 1
    assert unit_of_work.rollback_call_count == 0


def test_execute_success_leaves_expired_session_for_cleanup() -> None:
    """期限切れSessionではRuntimeと永続化先を操作せずCleanupへ委譲することを確認する。"""
    repository = FakeWorkspaceSessionRepository(_session(expires_at=NOW))
    runtime = FakeWorkspaceRuntime()
    unit_of_work = SpyUnitOfWork()

    DeleteWorkspace(repository, runtime, unit_of_work, FixedClock()).execute(
        DeleteWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID)
    )

    assert runtime.deleted_ids == []
    assert repository.deleted_ids == []
    assert unit_of_work.commit_call_count == 1
