from collections.abc import Sequence
from uuid import UUID

from src.textbook.application.ports import ChapterRepository
from src.textbook.application.queries import (
    ResolveChapterWorkspacePresetInput,
    ResolveChapterWorkspacePresetOutput,
)
from src.textbook.application.usecases import ResolveChapterWorkspacePreset
from src.textbook.domain.entities import Chapter, ChapterPosition, ContentString, TitleString

TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
WORKSPACE_PRESET_KEY = "ws-ubuntu-24_04"


class FakeChapterRepository(ChapterRepository):
    def __init__(self, chapters: Sequence[Chapter]) -> None:
        self._chapters = chapters

    def get(self, textbook_id: UUID, chapter_id: UUID) -> Chapter | None:
        return next(
            (chapter for chapter in self._chapters if chapter.textbook_id == textbook_id and chapter.id == chapter_id),
            None,
        )

    def list(self, textbook_id: UUID) -> Sequence[Chapter]:
        return tuple(chapter for chapter in self._chapters if chapter.textbook_id == textbook_id)


def _chapter(workspace_preset_key: str | None) -> Chapter:
    return Chapter(
        id=CHAPTER_ID,
        textbook_id=TEXTBOOK_ID,
        position=ChapterPosition(1),
        title=TitleString("第1章"),
        content=ContentString("第1章の本文"),
        workspace_preset_key=workspace_preset_key,
    )


def _input() -> ResolveChapterWorkspacePresetInput:
    return ResolveChapterWorkspacePresetInput(
        textbook_id=TEXTBOOK_ID,
        chapter_id=CHAPTER_ID,
    )


def test_execute_success_returns_workspace_preset_key_for_chapter() -> None:
    """Chapterに設定されたWorkspacePresetKeyを公開Queryから取得できることを確認する。"""
    query = ResolveChapterWorkspacePreset(FakeChapterRepository([_chapter(WORKSPACE_PRESET_KEY)]))

    output = query.execute(_input())

    assert output == ResolveChapterWorkspacePresetOutput(workspace_preset_key=WORKSPACE_PRESET_KEY)


def test_execute_success_returns_none_when_chapter_does_not_exist() -> None:
    """Chapterが存在しない場合は公開QueryがNoneを返すことを確認する。"""
    query = ResolveChapterWorkspacePreset(FakeChapterRepository([]))

    output = query.execute(_input())

    assert output is None


def test_execute_success_distinguishes_chapter_without_workspace_preset() -> None:
    """Chapterが存在してPresetが未設定の場合はPresetなしの出力を返すことを確認する。"""
    query = ResolveChapterWorkspacePreset(FakeChapterRepository([_chapter(None)]))

    output = query.execute(_input())

    assert output == ResolveChapterWorkspacePresetOutput(workspace_preset_key=None)
