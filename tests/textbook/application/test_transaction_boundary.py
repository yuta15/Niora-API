from uuid import UUID

import pytest
from pytest_mock import MockerFixture

from src.shared.application.ports import UnitOfWork
from src.textbook.application.models import GetChapterInput, GetTextbookInput
from src.textbook.application.ports import ChapterRepository, TextbookRepository
from src.textbook.application.usecases import GetChapter, GetTextbook, ListTextbooks
from src.textbook.domain.entities import Chapter, ChapterPosition, ContentString, Textbook, TitleString

TEXTBOOK_ID = UUID("50000000-0000-0000-0000-000000000001")
CHAPTER_ID = UUID("60000000-0000-0000-0000-000000000001")


class SpyUnitOfWork(UnitOfWork):
    """UseCaseが開始したTransactionの終了処理を観測するFake。"""

    def __init__(self) -> None:
        self.commit_call_count = 0
        self.rollback_call_count = 0

    def _commit(self) -> None:
        self.commit_call_count += 1

    def _rollback(self) -> None:
        self.rollback_call_count += 1


def test_list_textbooks_execute_success_commits_transaction(mocker: MockerFixture) -> None:
    """ListTextbooksが正常終了時にTransactionをcommitすることを確認する。"""
    repository = mocker.Mock(spec=TextbookRepository)
    repository.list.return_value = []
    unit_of_work = SpyUnitOfWork()

    ListTextbooks(repository, unit_of_work).execute()

    assert unit_of_work.commit_call_count == 1
    assert unit_of_work.rollback_call_count == 0


def test_list_textbooks_execute_failure_rolls_back_transaction(mocker: MockerFixture) -> None:
    """ListTextbooksがRepository例外時にTransactionをrollbackすることを確認する。"""
    repository = mocker.Mock(spec=TextbookRepository)
    repository.list.side_effect = RuntimeError("repository failed")
    unit_of_work = SpyUnitOfWork()

    with pytest.raises(RuntimeError, match="repository failed"):
        ListTextbooks(repository, unit_of_work).execute()

    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_get_textbook_execute_success_commits_shared_transaction(mocker: MockerFixture) -> None:
    """GetTextbookが両Repositoryの読み取りを1つのTransactionでcommitすることを確認する。"""
    textbook_repository = mocker.Mock(spec=TextbookRepository)
    textbook_repository.get.return_value = Textbook(id=TEXTBOOK_ID, title=TitleString("Python入門"))
    chapter_repository = mocker.Mock(spec=ChapterRepository)
    chapter_repository.list.return_value = []
    unit_of_work = SpyUnitOfWork()

    GetTextbook(textbook_repository, chapter_repository, unit_of_work).execute(
        GetTextbookInput(textbook_id=TEXTBOOK_ID)
    )

    assert unit_of_work.commit_call_count == 1
    assert unit_of_work.rollback_call_count == 0


def test_get_textbook_execute_failure_rolls_back_when_chapter_read_fails(mocker: MockerFixture) -> None:
    """GetTextbookの2つ目のRepositoryで失敗した場合にTransactionをrollbackすることを確認する。"""
    textbook_repository = mocker.Mock(spec=TextbookRepository)
    textbook_repository.get.return_value = Textbook(id=TEXTBOOK_ID, title=TitleString("Python入門"))
    chapter_repository = mocker.Mock(spec=ChapterRepository)
    chapter_repository.list.side_effect = RuntimeError("chapter repository failed")
    unit_of_work = SpyUnitOfWork()

    with pytest.raises(RuntimeError, match="chapter repository failed"):
        GetTextbook(textbook_repository, chapter_repository, unit_of_work).execute(
            GetTextbookInput(textbook_id=TEXTBOOK_ID)
        )

    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1


def test_get_chapter_execute_success_commits_and_returns_workspace_preset_key(mocker: MockerFixture) -> None:
    """GetChapterがTransactionをcommitしWorkspacePresetKeyをApplication出力へ含めることを確認する。"""
    repository = mocker.Mock(spec=ChapterRepository)
    repository.get.return_value = Chapter(
        id=CHAPTER_ID,
        textbook_id=TEXTBOOK_ID,
        position=ChapterPosition(0),
        title=TitleString("第1章"),
        content=ContentString("本文"),
        workspace_preset_key="python-basic",
    )
    unit_of_work = SpyUnitOfWork()

    output = GetChapter(repository, unit_of_work).execute(
        GetChapterInput(textbook_id=TEXTBOOK_ID, chapter_id=CHAPTER_ID)
    )

    assert output is not None
    assert output.workspace_preset_key == "python-basic"
    assert unit_of_work.commit_call_count == 1
    assert unit_of_work.rollback_call_count == 0


def test_get_chapter_execute_failure_rolls_back_transaction(mocker: MockerFixture) -> None:
    """GetChapterがRepository例外時にTransactionをrollbackすることを確認する。"""
    repository = mocker.Mock(spec=ChapterRepository)
    repository.get.side_effect = RuntimeError("chapter repository failed")
    unit_of_work = SpyUnitOfWork()

    with pytest.raises(RuntimeError, match="chapter repository failed"):
        GetChapter(repository, unit_of_work).execute(GetChapterInput(textbook_id=TEXTBOOK_ID, chapter_id=CHAPTER_ID))

    assert unit_of_work.commit_call_count == 0
    assert unit_of_work.rollback_call_count == 1
