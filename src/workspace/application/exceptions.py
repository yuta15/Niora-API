from uuid import UUID


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


class WorkspaceNotFoundError(Exception):
    """指定されたWorkspaceSessionに対応する実行環境が存在しない。"""

    def __init__(self, workspace_session_id: UUID) -> None:
        self.workspace_session_id = workspace_session_id
        super().__init__(f"workspace {workspace_session_id} was not found")
