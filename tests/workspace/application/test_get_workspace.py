from datetime import UTC, datetime
from uuid import UUID

import pytest

from src.workspace.application import WorkspaceNotFoundError
from src.workspace.application.models import (
    GetWorkspaceInput,
    GetWorkspaceOutput,
    WorkspaceComponentOutput,
)
from src.workspace.application.ports import WorkspaceRuntime, WorkspaceRuntimeSnapshot
from src.workspace.application.usecases import GetWorkspace
from src.workspace.domain.entities import (
    TerminalExecAccessPoint,
    WorkspaceComponent,
    WorkspaceDefinition,
    WorkspaceSession,
    WorkspaceStatus,
)

WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
WORKSPACE_DEFINITION_ID = UUID("0d4c3f6d-01fc-49da-8d72-b8a3a7f99425")
WORKSPACE_EXPIRES_AT = datetime(2026, 9, 14, tzinfo=UTC)


class FakeWorkspaceRuntime(WorkspaceRuntime):
    def __init__(self, snapshot: WorkspaceRuntimeSnapshot | None) -> None:
        self._snapshot = snapshot
        self.received_workspace_session_ids: list[UUID] = []

    def create(self, session: WorkspaceSession) -> None:
        raise AssertionError(f"unexpected workspace creation: {session.id}")

    def delete(self, workspace_session_id: UUID) -> None:
        raise AssertionError(f"unexpected workspace deletion: {workspace_session_id}")

    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        self.received_workspace_session_ids.append(workspace_session_id)
        return self._snapshot


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
    runtime = FakeWorkspaceRuntime(
        WorkspaceRuntimeSnapshot(
            session=session,
            definition=definition,
            status=WorkspaceStatus.READY,
        )
    )
    usecase = GetWorkspace(runtime)

    output = usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

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
    """Runtimeに対象Sessionが存在しない場合は明示的な例外を返すことを確認する。"""
    runtime = FakeWorkspaceRuntime(None)
    usecase = GetWorkspace(runtime)

    with pytest.raises(WorkspaceNotFoundError) as exception_info:
        usecase.execute(GetWorkspaceInput(workspace_session_id=WORKSPACE_SESSION_ID))

    assert runtime.received_workspace_session_ids == [WORKSPACE_SESSION_ID]
    assert exception_info.value.workspace_session_id == WORKSPACE_SESSION_ID
