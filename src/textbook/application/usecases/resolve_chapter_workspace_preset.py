from src.textbook.application.ports import ChapterRepository
from src.textbook.application.queries import (
    ChapterWorkspacePresetQuery,
    ResolveChapterWorkspacePresetInput,
    ResolveChapterWorkspacePresetOutput,
)


class ResolveChapterWorkspacePreset(ChapterWorkspacePresetQuery):
    """Chapterに紐づくWorkspacePresetKeyを解決する。"""

    def __init__(self, chapter_repository: ChapterRepository) -> None:
        self._chapter_repository = chapter_repository

    def execute(
        self,
        input: ResolveChapterWorkspacePresetInput,
    ) -> ResolveChapterWorkspacePresetOutput | None:
        """Chapterの存在とWorkspacePresetKeyの設定内容を返す。"""
        chapter = self._chapter_repository.get(input.textbook_id, input.chapter_id)
        if chapter is None:
            return None

        return ResolveChapterWorkspacePresetOutput(
            workspace_preset_key=chapter.workspace_preset_key,
        )
