from datetime import timedelta

from src.shared.application.ports import UnitOfWork
from src.textbook.application.queries import (
    ChapterWorkspacePresetQuery,
    ResolveChapterWorkspacePresetInput,
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
    WorkspaceSessionIdGenerator,
    WorkspaceSessionRepository,
)
from src.workspace.domain import WorkspacePresetKey, WorkspaceSession


class CreateWorkspace:
    """Chapterに対応する期限付きのWorkspaceを作成する。"""

    def __init__(
        self,
        chapter_workspace_preset_query: ChapterWorkspacePresetQuery,
        workspace_definition_id_resolver: WorkspaceDefinitionIdResolver,
        workspace_definition_repository: WorkspaceDefinitionRepository,
        workspace_session_repository: WorkspaceSessionRepository,
        workspace_runtime: WorkspaceRuntime,
        unit_of_work: UnitOfWork,
        clock: Clock,
        workspace_session_id_generator: WorkspaceSessionIdGenerator,
        lifetime: timedelta,
    ) -> None:
        if not isinstance(lifetime, timedelta):
            raise TypeError("workspace lifetime must be a timedelta")
        if lifetime <= timedelta(0):
            raise ValueError("workspace lifetime must be positive")

        self._chapter_workspace_preset_query = chapter_workspace_preset_query
        self._workspace_definition_id_resolver = workspace_definition_id_resolver
        self._workspace_definition_repository = workspace_definition_repository
        self._workspace_session_repository = workspace_session_repository
        self._workspace_runtime = workspace_runtime
        self._unit_of_work = unit_of_work
        self._clock = clock
        self._workspace_session_id_generator = workspace_session_id_generator
        self._lifetime = lifetime

    def execute(self, input: CreateWorkspaceInput) -> CreateWorkspaceOutput:
        """実行環境の作成要求を完了し、WorkspaceSessionの情報を返す。"""
        with self._unit_of_work:
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

            preset_key = WorkspacePresetKey(preset.workspace_preset_key)
            definition_id = self._workspace_definition_id_resolver.resolve(preset_key)
            if definition_id is None:
                raise WorkspaceDefinitionNotFoundError(preset_key)

            definition = self._workspace_definition_repository.get(definition_id)
            if definition is None:
                raise WorkspaceDefinitionNotFoundError(preset_key)

            expires_at = self._clock.now() + self._lifetime
            session = WorkspaceSession(
                id=self._workspace_session_id_generator.generate(),
                definition_id=definition.definition_id,
                expires_at=expires_at,
            )

        with self._unit_of_work:
            self._workspace_session_repository.add(session)

        self._workspace_runtime.create(session, definition)

        return CreateWorkspaceOutput(
            id=session.id,
            expires_at=session.expires_at,
        )
