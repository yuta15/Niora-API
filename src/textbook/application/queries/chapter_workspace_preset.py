from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ResolveChapterWorkspacePresetInput:
    """Chapterに紐づくWorkspacePresetKeyの解決に必要な入力。"""

    textbook_id: UUID
    chapter_id: UUID


@dataclass(frozen=True)
class ResolveChapterWorkspacePresetOutput:
    """存在するChapterに設定されたWorkspacePresetKey。"""

    workspace_preset_key: str | None


class ChapterWorkspacePresetQuery(ABC):
    """Chapterに紐づくWorkspacePresetKeyを公開するQuery契約。"""

    @abstractmethod
    def execute(
        self,
        input: ResolveChapterWorkspacePresetInput,
    ) -> ResolveChapterWorkspacePresetOutput | None:
        """Chapterが存在しない場合はNoneを返す。"""
