from uuid import UUID

from src.workspace.domain import WorkspacePresetKey


class ChapterNotFoundError(Exception):
    """Workspaceを作成する対象のChapterが存在しない。"""

    def __init__(self, textbook_id: UUID, chapter_id: UUID) -> None:
        self.textbook_id = textbook_id
        self.chapter_id = chapter_id
        super().__init__(f"chapter {chapter_id} was not found in textbook {textbook_id}")


class WorkspacePresetNotConfiguredError(Exception):
    """Workspaceを作成する対象のChapterにPresetが設定されていない。"""

    def __init__(self, textbook_id: UUID, chapter_id: UUID) -> None:
        self.textbook_id = textbook_id
        self.chapter_id = chapter_id
        super().__init__(f"workspace preset is not configured for chapter {chapter_id} in textbook {textbook_id}")


class WorkspaceDefinitionNotFoundError(Exception):
    """WorkspacePresetKeyに対応するWorkspaceDefinitionが存在しない。"""

    def __init__(self, preset_key: WorkspacePresetKey) -> None:
        self.preset_key = preset_key
        super().__init__(f"workspace definition was not found for preset {preset_key.value}")


class WorkspaceNotFoundError(Exception):
    """指定されたWorkspaceSessionに対応する実行環境が存在しない。"""

    def __init__(self, workspace_session_id: UUID) -> None:
        self.workspace_session_id = workspace_session_id
        super().__init__(f"workspace {workspace_session_id} was not found")


class WorkspaceSessionDefinitionNotFoundError(Exception):
    """WorkspaceSessionが参照するWorkspaceDefinitionが存在しない。"""

    def __init__(self, definition_id: UUID) -> None:
        self.definition_id = definition_id
        super().__init__(f"workspace definition {definition_id} referenced by a session was not found")
