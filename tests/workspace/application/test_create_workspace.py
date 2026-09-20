from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.shared.application.ports import UnitOfWork
from src.textbook.application.queries import (
    ChapterWorkspacePresetQuery,
    ResolveChapterWorkspacePresetInput,
    ResolveChapterWorkspacePresetOutput,
)
from src.workspace.application import (
    ChapterNotFoundError,
    WorkspaceDefinitionNotFoundError,
    WorkspacePresetNotConfiguredError,
)
from src.workspace.application.models import CreateWorkspaceInput, CreateWorkspaceOutput
from src.workspace.application.ports import (
    Clock,
    WorkspaceDefinitionIdResolver,
    WorkspaceDefinitionRepository,
    WorkspaceRuntime,
    WorkspaceRuntimeSnapshot,
    WorkspaceSessionIdGenerator,
    WorkspaceSessionRepository,
)
from src.workspace.application.usecases import CreateWorkspace
from src.workspace.domain import WorkspaceComponent, WorkspaceDefinition, WorkspacePresetKey, WorkspaceSession

TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
WORKSPACE_DEFINITION_ID = UUID("dd1c64fa-8763-4f06-aa92-929d08d04dd0")
WORKSPACE_PRESET_KEY = "ws-ubuntu-24_04"
NOW = datetime(2026, 8, 26, 10, 0, tzinfo=UTC)
LIFETIME = timedelta(hours=2)


class FakeChapterWorkspacePresetQuery(ChapterWorkspacePresetQuery):
    def __init__(self, output: ResolveChapterWorkspacePresetOutput | None) -> None:
        self._output = output
        self.received_inputs: list[ResolveChapterWorkspacePresetInput] = []

    def execute(
        self,
        input: ResolveChapterWorkspacePresetInput,
    ) -> ResolveChapterWorkspacePresetOutput | None:
        self.received_inputs.append(input)
        return self._output


class FakeWorkspaceRuntime(WorkspaceRuntime):
    def __init__(self, create_error: Exception | None = None) -> None:
        self._create_error = create_error
        self.created_workspaces: list[tuple[WorkspaceSession, WorkspaceDefinition]] = []

    def create(self, session: WorkspaceSession, definition: WorkspaceDefinition) -> None:
        self.created_workspaces.append((session, definition))
        if self._create_error is not None:
            raise self._create_error

    def delete(self, workspace_session_id: UUID) -> None:
        raise AssertionError(f"unexpected workspace deletion: {workspace_session_id}")

    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        raise AssertionError(f"unexpected workspace lookup: {workspace_session_id}")


class FakeWorkspaceDefinitionIdResolver(WorkspaceDefinitionIdResolver):
    def __init__(self, definition_id: UUID | None) -> None:
        self._definition_id = definition_id
        self.received_preset_keys: list[WorkspacePresetKey] = []

    def resolve(self, preset_key: WorkspacePresetKey) -> UUID | None:
        self.received_preset_keys.append(preset_key)
        return self._definition_id


class FakeWorkspaceDefinitionRepository(WorkspaceDefinitionRepository):
    def __init__(self, definition: WorkspaceDefinition | None) -> None:
        self._definition = definition
        self.received_definition_ids: list[UUID] = []

    def get(self, definition_id: UUID) -> WorkspaceDefinition | None:
        self.received_definition_ids.append(definition_id)
        return self._definition


class FakeWorkspaceSessionRepository(WorkspaceSessionRepository):
    def __init__(self, add_error: Exception | None = None) -> None:
        self._add_error = add_error
        self.added_sessions: list[WorkspaceSession] = []

    def get(self, id: UUID) -> WorkspaceSession | None:
        raise AssertionError(f"unexpected workspace session lookup: {id}")

    def add(self, session: WorkspaceSession) -> None:
        self.added_sessions.append(session)
        if self._add_error is not None:
            raise self._add_error

    def delete(self, id: UUID) -> None:
        raise AssertionError(f"unexpected workspace session deletion: {id}")


class SpyUnitOfWork(UnitOfWork):
    def __init__(self, commit_error_on_call: int | None = None) -> None:
        self._commit_error_on_call = commit_error_on_call
        self.commit_call_count = 0
        self.rollback_call_count = 0

    def _commit(self) -> None:
        self.commit_call_count += 1
        if self.commit_call_count == self._commit_error_on_call:
            raise RuntimeError("commit failed")

    def _rollback(self) -> None:
        self.rollback_call_count += 1


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


class FixedWorkspaceSessionIdGenerator(WorkspaceSessionIdGenerator):
    def generate(self) -> UUID:
        return WORKSPACE_SESSION_ID


def _input() -> CreateWorkspaceInput:
    return CreateWorkspaceInput(
        textbook_id=TEXTBOOK_ID,
        chapter_id=CHAPTER_ID,
    )


def _usecase(
    query_output: ResolveChapterWorkspacePresetOutput | None,
    lifetime: timedelta = LIFETIME,
    definition_id: UUID | None = WORKSPACE_DEFINITION_ID,
    definition: WorkspaceDefinition | None = None,
    definition_exists: bool = True,
    runtime_create_error: Exception | None = None,
    session_repository_add_error: Exception | None = None,
    commit_error_on_call: int | None = None,
) -> tuple[
    CreateWorkspace,
    FakeChapterWorkspacePresetQuery,
    FakeWorkspaceDefinitionIdResolver,
    FakeWorkspaceDefinitionRepository,
    FakeWorkspaceSessionRepository,
    FakeWorkspaceRuntime,
    SpyUnitOfWork,
]:
    query = FakeChapterWorkspacePresetQuery(query_output)
    definition_id_resolver = FakeWorkspaceDefinitionIdResolver(definition_id)
    if definition is None and definition_id is not None and definition_exists:
        definition = WorkspaceDefinition(
            definition_id=definition_id,
            components=(WorkspaceComponent(component_key="ubuntu", image="ubuntu:latest"),),
        )
    definition_repository = FakeWorkspaceDefinitionRepository(definition)
    session_repository = FakeWorkspaceSessionRepository(session_repository_add_error)
    runtime = FakeWorkspaceRuntime(runtime_create_error)
    unit_of_work = SpyUnitOfWork(commit_error_on_call)
    usecase = CreateWorkspace(
        chapter_workspace_preset_query=query,
        workspace_definition_id_resolver=definition_id_resolver,
        workspace_definition_repository=definition_repository,
        workspace_session_repository=session_repository,
        workspace_runtime=runtime,
        unit_of_work=unit_of_work,
        clock=FixedClock(),
        workspace_session_id_generator=FixedWorkspaceSessionIdGenerator(),
        lifetime=lifetime,
    )
    return usecase, query, definition_id_resolver, definition_repository, session_repository, runtime, unit_of_work


def test_execute_success_creates_workspace_session_for_chapter() -> None:
    """ChapterのPresetから固定IDと期限を持つSessionを作成し、Runtimeへ渡すことを確認する。"""
    usecase, query, definition_id_resolver, definition_repository, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY)
    )

    output = usecase.execute(_input())

    assert query.received_inputs == [
        ResolveChapterWorkspacePresetInput(
            textbook_id=TEXTBOOK_ID,
            chapter_id=CHAPTER_ID,
        )
    ]
    assert output == CreateWorkspaceOutput(
        id=WORKSPACE_SESSION_ID,
        expires_at=NOW + LIFETIME,
    )
    assert definition_id_resolver.received_preset_keys == [WorkspacePresetKey(WORKSPACE_PRESET_KEY)]
    assert definition_repository.received_definition_ids == [WORKSPACE_DEFINITION_ID]
    assert len(runtime.created_workspaces) == 1
    session, definition = runtime.created_workspaces[0]
    assert session.id == WORKSPACE_SESSION_ID
    assert session.definition_id == WORKSPACE_DEFINITION_ID
    assert session.expires_at == NOW + LIFETIME
    assert definition.definition_id == WORKSPACE_DEFINITION_ID
    assert session_repository.added_sessions == [session]
    assert unit_of_work.commit_call_count == 2


def test_execute_failure_returns_create_error_after_saving_session() -> None:
    """Runtime作成失敗時はSessionを残し、作成エラーを返すことを確認する。"""
    create_error = RuntimeError("runtime creation failed")
    usecase, _, _, _, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
        runtime_create_error=create_error,
    )

    with pytest.raises(RuntimeError, match="runtime creation failed") as exception_info:
        usecase.execute(_input())

    assert exception_info.value is create_error
    assert session_repository.added_sessions[0].id == WORKSPACE_SESSION_ID
    assert len(runtime.created_workspaces) == 1
    assert unit_of_work.commit_call_count == 2


def test_execute_failure_does_not_call_runtime_when_session_save_fails() -> None:
    """Session保存失敗時はRuntimeを呼ばず、保存エラーを返すことを確認する。"""
    save_error = RuntimeError("session save failed")
    usecase, _, _, _, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
        session_repository_add_error=save_error,
    )

    with pytest.raises(RuntimeError, match="session save failed") as exception_info:
        usecase.execute(_input())

    assert exception_info.value is save_error
    assert session_repository.added_sessions[0].id == WORKSPACE_SESSION_ID
    assert runtime.created_workspaces == []
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_does_not_call_runtime_when_session_commit_fails() -> None:
    """Session commit失敗時はRuntimeを呼ばず、commitエラーを返すことを確認する。"""
    usecase, _, _, _, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
        commit_error_on_call=2,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        usecase.execute(_input())

    assert session_repository.added_sessions[0].id == WORKSPACE_SESSION_ID
    assert runtime.created_workspaces == []
    assert unit_of_work.commit_call_count == 2
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_when_chapter_does_not_exist() -> None:
    """Chapterが存在しない場合は明示的な例外を返し、Runtimeを呼ばないことを確認する。"""
    usecase, _, definition_id_resolver, definition_repository, session_repository, runtime, unit_of_work = _usecase(
        None
    )

    with pytest.raises(ChapterNotFoundError) as exception_info:
        usecase.execute(_input())

    assert exception_info.value.textbook_id == TEXTBOOK_ID
    assert exception_info.value.chapter_id == CHAPTER_ID
    assert definition_id_resolver.received_preset_keys == []
    assert definition_repository.received_definition_ids == []
    assert runtime.created_workspaces == []
    assert session_repository.added_sessions == []
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_when_workspace_preset_is_not_configured() -> None:
    """Presetが未設定の場合は明示的な例外を返し、Runtimeを呼ばないことを確認する。"""
    usecase, _, definition_id_resolver, definition_repository, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=None)
    )

    with pytest.raises(WorkspacePresetNotConfiguredError) as exception_info:
        usecase.execute(_input())

    assert exception_info.value.textbook_id == TEXTBOOK_ID
    assert exception_info.value.chapter_id == CHAPTER_ID
    assert definition_id_resolver.received_preset_keys == []
    assert definition_repository.received_definition_ids == []
    assert runtime.created_workspaces == []
    assert session_repository.added_sessions == []
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_when_workspace_definition_does_not_exist() -> None:
    """Presetに対応するWorkspaceDefinitionが存在しない場合はRuntimeを呼ばないことを確認する。"""
    usecase, _, definition_id_resolver, definition_repository, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
        definition_id=None,
    )

    with pytest.raises(WorkspaceDefinitionNotFoundError) as exception_info:
        usecase.execute(_input())

    assert exception_info.value.preset_key == WorkspacePresetKey(WORKSPACE_PRESET_KEY)
    assert definition_id_resolver.received_preset_keys == [WorkspacePresetKey(WORKSPACE_PRESET_KEY)]
    assert definition_repository.received_definition_ids == []
    assert runtime.created_workspaces == []
    assert session_repository.added_sessions == []
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_execute_failure_raises_when_resolved_workspace_definition_does_not_exist() -> None:
    """対応表のIDにDefinitionがない場合は、Runtimeを呼ばずread transactionをrollbackする。"""
    usecase, _, _, definition_repository, session_repository, runtime, unit_of_work = _usecase(
        ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
        definition_exists=False,
    )

    with pytest.raises(WorkspaceDefinitionNotFoundError):
        usecase.execute(_input())

    assert definition_repository.received_definition_ids == [WORKSPACE_DEFINITION_ID]
    assert runtime.created_workspaces == []
    assert session_repository.added_sessions == []
    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(microseconds=-1)])
def test_init_failure_rejects_non_positive_workspace_lifetime(lifetime: timedelta) -> None:
    """0以下の有効期間ではCreateWorkspaceを構築できないことを確認する。"""
    with pytest.raises(ValueError, match="workspace lifetime must be positive"):
        _usecase(
            ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
            lifetime=lifetime,
        )
