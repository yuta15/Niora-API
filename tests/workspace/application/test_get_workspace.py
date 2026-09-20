from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.shared.application.ports import UnitOfWork
from src.workspace.application import (
    WorkspaceNotFoundError,
    WorkspaceSessionDefinitionNotFoundError,
)
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
from src.workspace.application.ports import (
    Clock,
    WorkspaceDefinitionRepository,
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


class FakeWorkspaceDefinitionRepository(WorkspaceDefinitionRepository):
    def __init__(self, definition: WorkspaceDefinition | None) -> None:
        self._definition = definition
        self.received_definition_ids: list[UUID] = []

    def get(self, definition_id: UUID) -> WorkspaceDefinition | None:
        self.received_definition_ids.append(definition_id)
        return self._definition


class FixedClock(Clock):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class SpyUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.commit_call_count = 0

    def _commit(self) -> None:
        self.commit_call_count += 1

    def _rollback(self) -> None:
        pass


def _usecase(
    session: WorkspaceSession | None,
    definition: WorkspaceDefinition | None,
    snapshot: WorkspaceRuntimeSnapshot | None,
    now: datetime = NOW,
) -> tuple[
    GetWorkspace,
    FakeWorkspaceSessionRepository,
    FakeWorkspaceDefinitionRepository,
    FakeWorkspaceRuntime,
    SpyUnitOfWork,
]:
    session_repository = FakeWorkspaceSessionRepository(session)
    definition_repository = FakeWorkspaceDefinitionRepository(definition)
    runtime = FakeWorkspaceRuntime(snapshot)
    unit_of_work = SpyUnitOfWork()
    usecase = GetWorkspace(
        session_repository,
        definition_repository,
        runtime,
        unit_of_work,
        FixedClock(now),
    )
    return usecase, session_repository, definition_repository, runtime, unit_of_work


def test_execute_success_returns_database_session_and_definition_with_runtime_status() -> None:
    """DBのSessionとDefinition、およびRuntimeの状態を組み合わせて返す。"""
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
    usecase, session_repository, definition_repository, runtime, unit_of_work = _usecase(
        session,
        definition,
        WorkspaceRuntimeSnapshot(status=WorkspaceStatus.READY),
    )

    output = usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert session_repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert definition_repository.received_definition_ids == [WORKSPACE_DEFINITION_ID]
    assert runtime.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert unit_of_work.commit_call_count == 1
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
    usecase, repository, definition_repository, runtime, _ = _usecase(None, None, None)

    with pytest.raises(WorkspaceNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert definition_repository.received_definition_ids == []
    assert runtime.received_workspace_session_ids == []
    assert exception_info.value.workspace_session_id == WORKSPACE_SESSION_ID


def test_execute_failure_rejects_expired_workspace_before_runtime_lookup() -> None:
    """期限切れSessionはRuntimeを呼ばず例外を返すことを確認する。"""
    session = WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=NOW,
    )
    usecase, repository, definition_repository, runtime, _ = _usecase(session, None, None)

    with pytest.raises(WorkspaceNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert repository.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert definition_repository.received_definition_ids == []
    assert runtime.received_workspace_session_ids == []
    assert exception_info.value.workspace_session_id == WORKSPACE_SESSION_ID


def test_execute_success_returns_missing_when_runtime_workspace_is_absent() -> None:
    """永続化されたSessionは有効だがRuntimeがない場合はmissing状態を返す。"""
    session = WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=WORKSPACE_EXPIRES_AT,
    )
    definition = WorkspaceDefinition(
        definition_id=WORKSPACE_DEFINITION_ID,
        components=(WorkspaceComponent(component_key="ubuntu", image="ubuntu:latest"),),
    )
    usecase, _, _, runtime, _ = _usecase(session, definition, None)

    output = usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert runtime.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert output == GetWorkspaceOutput(
        session_id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=WORKSPACE_EXPIRES_AT,
        status=WorkspaceStatus.MISSING,
        components=(
            WorkspaceComponentOutput(
                component_key="ubuntu",
                image="ubuntu:latest",
                terminal_exec_available=False,
            ),
        ),
    )


def test_execute_failure_raises_when_session_definition_is_missing_without_runtime_lookup() -> None:
    """参照Definitionが欠損している場合はRuntimeを呼ばず識別子付き例外を返す。"""
    session = WorkspaceSession(
        id=WORKSPACE_SESSION_ID,
        definition_id=WORKSPACE_DEFINITION_ID,
        expires_at=WORKSPACE_EXPIRES_AT,
    )
    usecase, _, definition_repository, runtime, _ = _usecase(session, None, None)

    with pytest.raises(WorkspaceSessionDefinitionNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert definition_repository.received_definition_ids == [WORKSPACE_DEFINITION_ID]
    assert runtime.received_workspace_session_ids == []
    assert exception_info.value.definition_id == WORKSPACE_DEFINITION_ID
