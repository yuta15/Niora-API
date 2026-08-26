from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from src.textbook.application.queries import (
    ChapterWorkspacePresetQuery,
    ResolveChapterWorkspacePresetInput,
    ResolveChapterWorkspacePresetOutput,
)
from src.workspace.application import ChapterNotFoundError, WorkspacePresetNotConfiguredError
from src.workspace.application.models import CreateWorkspaceInput, CreateWorkspaceOutput
from src.workspace.application.ports import (
    Clock,
    WorkspaceRuntime,
    WorkspaceRuntimeSnapshot,
    WorkspaceSessionIdGenerator,
)
from src.workspace.application.usecases import CreateWorkspace
from src.workspace.domain.entities import WorkspacePresetKey, WorkspaceSession

TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
WORKSPACE_SESSION_ID = UUID("b578c2b7-d5c2-4275-97be-a89665729719")
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
    def __init__(self) -> None:
        self.created_sessions: list[WorkspaceSession] = []

    def create(self, session: WorkspaceSession) -> None:
        self.created_sessions.append(session)

    def delete(self, workspace_session_id: UUID) -> None:
        raise AssertionError(f"unexpected workspace deletion: {workspace_session_id}")

    def find(self, workspace_session_id: UUID) -> WorkspaceRuntimeSnapshot | None:
        raise AssertionError(f"unexpected workspace lookup: {workspace_session_id}")


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
) -> tuple[CreateWorkspace, FakeChapterWorkspacePresetQuery, FakeWorkspaceRuntime]:
    query = FakeChapterWorkspacePresetQuery(query_output)
    runtime = FakeWorkspaceRuntime()
    usecase = CreateWorkspace(
        chapter_workspace_preset_query=query,
        workspace_runtime=runtime,
        clock=FixedClock(),
        workspace_session_id_generator=FixedWorkspaceSessionIdGenerator(),
        lifetime=lifetime,
    )
    return usecase, query, runtime


def test_execute_success_creates_workspace_session_for_chapter() -> None:
    """ChapterのPresetから固定IDと期限を持つSessionを作成し、Runtimeへ渡すことを確認する。"""
    usecase, query, runtime = _usecase(ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY))

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
    assert len(runtime.created_sessions) == 1
    session = runtime.created_sessions[0]
    assert session.id == WORKSPACE_SESSION_ID
    assert session.preset_key == WorkspacePresetKey(WORKSPACE_PRESET_KEY)
    assert session.expires_at == NOW + LIFETIME


def test_execute_failure_raises_when_chapter_does_not_exist() -> None:
    """Chapterが存在しない場合は明示的な例外を返し、Runtimeを呼ばないことを確認する。"""
    usecase, _, runtime = _usecase(None)

    with pytest.raises(ChapterNotFoundError) as exception_info:
        usecase.execute(_input())

    assert exception_info.value.textbook_id == TEXTBOOK_ID
    assert exception_info.value.chapter_id == CHAPTER_ID
    assert runtime.created_sessions == []


def test_execute_failure_raises_when_workspace_preset_is_not_configured() -> None:
    """Presetが未設定の場合は明示的な例外を返し、Runtimeを呼ばないことを確認する。"""
    usecase, _, runtime = _usecase(ResolveChapterWorkspacePresetOutput(workspace_preset_key=None))

    with pytest.raises(WorkspacePresetNotConfiguredError) as exception_info:
        usecase.execute(_input())

    assert exception_info.value.textbook_id == TEXTBOOK_ID
    assert exception_info.value.chapter_id == CHAPTER_ID
    assert runtime.created_sessions == []


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(microseconds=-1)])
def test_init_failure_rejects_non_positive_workspace_lifetime(lifetime: timedelta) -> None:
    """0以下の有効期間ではCreateWorkspaceを構築できないことを確認する。"""
    with pytest.raises(ValueError, match="workspace lifetime must be positive"):
        _usecase(
            ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY),
            lifetime=lifetime,
        )
