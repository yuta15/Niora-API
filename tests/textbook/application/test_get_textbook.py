from collections.abc import Sequence
from uuid import UUID

from src.shared.application.ports import UnitOfWork
from src.textbook.application.models import (
    ChapterSummary,
    GetTextbookInput,
    GetTextbookOutput,
)
from src.textbook.application.ports import ChapterRepository, TextbookRepository
from src.textbook.application.usecases import GetTextbook
from src.textbook.domain.entities import (
    Chapter,
    ChapterPosition,
    ContentString,
    Textbook,
    TitleString,
)

TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
FIRST_CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
SECOND_CHAPTER_ID = UUID("8498bf44-f8f8-42e8-bdb6-5f60b2b51b7c")


class FakeUnitOfWork(UnitOfWork):
    """GetTextbookのTransaction境界を実行するFake。"""

    def _commit(self) -> None:
        pass

    def _rollback(self) -> None:
        pass


class FakeTextbookRepository(TextbookRepository):
    def __init__(self, textbooks: Sequence[Textbook]) -> None:
        self._textbooks = textbooks

    def get(self, textbook_id: UUID) -> Textbook | None:
        return next((textbook for textbook in self._textbooks if textbook.id == textbook_id), None)

    def list(self) -> list[Textbook]:
        return list(self._textbooks)


class FakeChapterRepository(ChapterRepository):
    def __init__(self, chapters: Sequence[Chapter]) -> None:
        self._chapters = chapters
        self.list_call_count = 0

    def get(self, textbook_id: UUID, chapter_id: UUID) -> Chapter | None:
        return next(
            (chapter for chapter in self._chapters if chapter.textbook_id == textbook_id and chapter.id == chapter_id),
            None,
        )

    def list(self, textbook_id: UUID) -> Sequence[Chapter]:
        self.list_call_count += 1
        return tuple(chapter for chapter in self._chapters if chapter.textbook_id == textbook_id)


def test_execute_success_returns_textbook_with_chapters() -> None:
    """教科書と位置順の章が表示用の形式へ変換されることを確認する。"""
    textbook_repository = FakeTextbookRepository([Textbook(id=TEXTBOOK_ID, title=TitleString("教科書のタイトル"))])
    chapter_repository = FakeChapterRepository(
        [
            Chapter(
                id=FIRST_CHAPTER_ID,
                textbook_id=TEXTBOOK_ID,
                position=ChapterPosition(1),
                title=TitleString("第1章"),
                content=ContentString("第1章の本文"),
            ),
            Chapter(
                id=SECOND_CHAPTER_ID,
                textbook_id=TEXTBOOK_ID,
                position=ChapterPosition(2),
                title=TitleString("第2章"),
                content=ContentString("第2章の本文"),
            ),
        ]
    )
    usecase = GetTextbook(textbook_repository, chapter_repository, FakeUnitOfWork())

    output = usecase.execute(GetTextbookInput(textbook_id=TEXTBOOK_ID))

    assert output == GetTextbookOutput(
        id=TEXTBOOK_ID,
        title="教科書のタイトル",
        chapters=(
            ChapterSummary(id=FIRST_CHAPTER_ID, title="第1章", position=1),
            ChapterSummary(id=SECOND_CHAPTER_ID, title="第2章", position=2),
        ),
    )


def test_execute_success_returns_none_without_loading_chapters_when_textbook_does_not_exist() -> None:
    """教科書が存在しない場合は章を取得せずNoneを返すことを確認する。"""
    chapter_repository = FakeChapterRepository([])
    usecase = GetTextbook(FakeTextbookRepository([]), chapter_repository, FakeUnitOfWork())

    output = usecase.execute(GetTextbookInput(textbook_id=TEXTBOOK_ID))

    assert output is None
    assert chapter_repository.list_call_count == 0
