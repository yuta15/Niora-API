from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.shared.application.ports import UnitOfWork
from src.workspace.application import WorkspaceNotFoundError
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
from src.workspace.application.ports import (
    Clock,
    WorkspaceRuntime,
    WorkspaceRuntimeSnapshot,
    WorkspaceSessionRepository,
)
from src.workspace.application.usecases import GetWorkspace
from src.workspace.domain import (
    TerminalExecAccessPoint,
    WorkspaceComponent,
    WorkspaceDefinition,
    WorkspaceSession,
    WorkspaceStatus,
)

WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
WORKSPACE_DEFINITION_ID = UUID("0d4c3f6d-01fc-49da-8d72-b8a3a7f99425")
WORKSPACE_EXPIRES_AT = datetime(2026, 9, 14, tzinfo=UTC)
NOW = datetime(2026, 9, 13, tzinfo=UTC)


class FakeWorkspaceRuntime(WorkspaceRuntime):
    def __init__(self, snapshot: WorkspaceRuntimeSnapshot | None) -> None:
        self._snapshot = snapshot
        self.received_workspace_session_ids: list[UUID] = []

    def create(self, session: WorkspaceSession, definition: WorkspaceDefinition) -> None:
        raise AssertionError(f"unexpected workspace creation: {session.id}")

    def delete(self, workspace_session_id: UUID) -> None:
        raise AssertionError(f"unexpected workspace deletion: {workspace_session_id}")

    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        self.received_workspace_session_ids.append(workspace_session_id)
        return self._snapshot


class FakeWorkspaceSessionRepository(WorkspaceSessionRepository):
    def __init__(self, session: WorkspaceSession | None) -> None:
        self._session = session
        self.received_workspace_session_ids: list[UUID] = []

    def get(self, id: UUID) -> WorkspaceSession | None:
        self.received_workspace_session_ids.append(id)
        return self._session

    def add(self, session: WorkspaceSession) -> None:
        raise AssertionError(f"unexpected workspace session addition: {session.id}")

    def delete(self, id: UUID) -> None:
        raise AssertionError(f"unexpected workspace session deletion: {id}")


class FixedClock(Clock):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SpyUnitOfWork(UnitOfWork):
    def _commit(self) -> None:
        pass

    def _rollback(self) -> None:
        pass


def _usecase(
    session: WorkspaceSession | None,
    snapshot: WorkspaceRuntimeSnapshot | None,
    now: datetime = NOW,
) -> tuple[GetWorkspace, FakeWorkspaceSessionRepository, FakeWorkspaceRuntime]:
    repository = FakeWorkspaceSessionRepository(session)
    runtime = FakeWorkspaceRuntime(snapshot)
    usecase = GetWorkspace(repository, runtime, SpyUnitOfWork(), FixedClock(now))
    return usecase, repository, runtime


def test_execute_success_returns_workspace_runtime_snapshot() -> None:
    """指定したSessionの情報、Definitionの構成、および状態を返すことを確認する。"""
    session = WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=WORKSPACE_EXPIRES_AT,
    )
    definition = WorkspaceDefinition(
        definition_id=WORKSPACE_DEFINITION_ID,
        components=(
            WorkspaceComponent(
                component_key="ubuntu",
                image="ubuntu:latest",
                startup_command=("sleep", "infinity"),
                terminal_exec=TerminalExecAccessPoint(("/bin/bash",)),
            ),
            WorkspaceComponent(
                component_key="database",
                image="mysql:9.7",
            ),
        ),
    )
    usecase, repository, runtime = _usecase(
        session,
        WorkspaceRuntimeSnapshot(session=session, definition=definition, status=WorkspaceStatus.READY),
    )

    output = usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert runtime.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert output == GetWorkspaceOutput(
        session_id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=WORKSPACE_EXPIRES_AT,
        status=WorkspaceStatus.READY,
        components=(
            WorkspaceComponentOutput(
                component_key="ubuntu",
                image="ubuntu:latest",
                terminal_exec_available=True,
            ),
            WorkspaceComponentOutput(
                component_key="database",
                image="mysql:9.7",
                terminal_exec_available=False,
            ),
        ),
    )


def test_execute_failure_raises_when_workspace_does_not_exist() -> None:
    """永続化されたSessionがない場合はRuntimeを呼ばず例外を返すことを確認する。"""
    usecase, repository, runtime = _usecase(None, None)

    with pytest.raises(WorkspaceNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert runtime.received_workspace_session_ids == []
    assert exception_info.value.workspace_session_id == WORKSPACE_SESSION_ID


def test_execute_failure_rejects_expired_workspace_before_runtime_lookup() -> None:
    """期限切れSessionはRuntimeを呼ばず例外を返すことを確認する。"""
    session = WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=NOW,
    )
    usecase, repository, runtime = _usecase(session, None)

    with pytest.raises(WorkspaceNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert runtime.received_workspace_session_ids == []
    assert exception_info.value.workspace_session_id == WORKSPACE_SESSION_ID
