from datetime import timedelta

from src.textbook.application.queries import (
    ChapterWorkspacePresetQuery,
    ResolveChapterWorkspacePresetInput,
)
from src.workspace.application.exceptions import ChapterNotFoundError, WorkspacePresetNotConfiguredError
from src.workspace.application.models import CreateWorkspaceInput, CreateWorkspaceOutput
from src.workspace.application.ports import Clock, WorkspaceRuntime, WorkspaceSessionIdGenerator
from src.workspace.domain.entities import WorkspacePresetKey, WorkspaceSession


class CreateWorkspace:
    """Chapterに対応する期限付きのWorkspaceを作成する。"""

    def __init__(
        self,
        chapter_workspace_preset_query: ChapterWorkspacePresetQuery,
        workspace_runtime: WorkspaceRuntime,
        clock: Clock,
        workspace_session_id_generator: WorkspaceSessionIdGenerator,
        lifetime: timedelta,
    ) -> None:
        if not isinstance(lifetime, timedelta):
            raise TypeError("workspace lifetime must be a timedelta")
        if lifetime <= timedelta(0):
            raise ValueError("workspace lifetime must be positive")

        self._chapter_workspace_preset_query = chapter_workspace_preset_query
        self._workspace_runtime = workspace_runtime
        self._clock = clock
        self._workspace_session_id_generator = workspace_session_id_generator
        self._lifetime = lifetime

    def execute(self, input: CreateWorkspaceInput) -> CreateWorkspaceOutput:
        """実行環境の作成要求を完了し、WorkspaceSessionの情報を返す。"""
        preset = self._chapter_workspace_preset_query.execute(
            ResolveChapterWorkspacePresetInput(
                textbook_id=input.textbook_id,
                chapter_id=input.chapter_id,
            )
        )
        if preset is None:
            raise ChapterNotFoundError(input.textbook_id, input.chapter_id)
        if preset.workspace_preset_key is None:
            raise WorkspacePresetNotConfiguredError(input.textbook_id, input.chapter_id)

        expires_at = self._clock.now() + self._lifetime
        session = WorkspaceSession(
            id=self._workspace_session_id_generator.generate(),
            preset_key=WorkspacePresetKey(preset.workspace_preset_key),
            expires_at=expires_at,
        )
        self._workspace_runtime.create(session)

        return CreateWorkspaceOutput(
            id=session.id,
            expires_at=session.expires_at,
        )
