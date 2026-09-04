from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.textbook.infra.database import ChapterTable, SqlAlchemyChapterRepository, TextbookTable


def _store_textbooks(mysql_session: Session, *textbook_ids: UUID) -> None:
    """Chapterテストに必要なTextbookを保存する。"""
    mysql_session.add_all(
        TextbookTable(id=textbook_id, title=f"Textbook {index}") for index, textbook_id in enumerate(textbook_ids)
    )
    mysql_session.flush()


@pytest.mark.integration
def test_list_success_filters_by_textbook_and_orders_by_position(mysql_session: Session) -> None:
    """Chapter一覧がTextbookで絞られpositionの昇順で返ることを確認する。"""
    textbook_id = UUID("10000000-0000-0000-0000-000000000001")
    other_textbook_id = UUID("10000000-0000-0000-0000-000000000002")
    _store_textbooks(mysql_session, textbook_id, other_textbook_id)
    mysql_session.add_all(
        [
            ChapterTable(
                id=UUID("20000000-0000-0000-0000-000000000003"),
                textbook_id=textbook_id,
                title="第3章",
                position=2,
                content="third",
                workspace_preset_key=None,
            ),
            ChapterTable(
                id=UUID("20000000-0000-0000-0000-000000000001"),
                textbook_id=textbook_id,
                title="第1章",
                position=0,
                content="first",
                workspace_preset_key=None,
            ),
            ChapterTable(
                id=UUID("20000000-0000-0000-0000-000000000004"),
                textbook_id=other_textbook_id,
                title="別の教科書",
                position=0,
                content="other",
                workspace_preset_key=None,
            ),
            ChapterTable(
                id=UUID("20000000-0000-0000-0000-000000000002"),
                textbook_id=textbook_id,
                title="第2章",
                position=1,
                content="second",
                workspace_preset_key=None,
            ),
        ]
    )
    mysql_session.commit()
    repository = SqlAlchemyChapterRepository(mysql_session)

    chapters = repository.list(textbook_id)

    assert [chapter.position.value for chapter in chapters] == [0, 1, 2]
    assert [chapter.textbook_id for chapter in chapters] == [textbook_id, textbook_id, textbook_id]


@pytest.mark.integration
@pytest.mark.parametrize("workspace_preset_key", [None, "python-basic"])
def test_get_success_returns_chapter_with_workspace_preset_key(
    mysql_session: Session,
    workspace_preset_key: str | None,
) -> None:
    """ChapterをDomain Entityへ変換するときWorkspacePresetKeyの有無を維持することを確認する。"""
    textbook_id = UUID("10000000-0000-0000-0000-000000000001")
    chapter_id = UUID("20000000-0000-0000-0000-000000000001")
    _store_textbooks(mysql_session, textbook_id)
    mysql_session.add(
        ChapterTable(
            id=chapter_id,
            textbook_id=textbook_id,
            title="第1章",
            position=0,
            content="print('hello')",
            workspace_preset_key=workspace_preset_key,
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyChapterRepository(mysql_session)

    chapter = repository.get(textbook_id, chapter_id)

    assert chapter is not None
    assert chapter.id == chapter_id
    assert chapter.textbook_id == textbook_id
    assert chapter.position.value == 0
    assert chapter.title.value == "第1章"
    assert chapter.content.value == "print('hello')"
    assert chapter.workspace_preset_key == workspace_preset_key


@pytest.mark.integration
@pytest.mark.parametrize(
    ("lookup_textbook_id", "lookup_chapter_id"),
    [
        (
            UUID("10000000-0000-0000-0000-000000000002"),
            UUID("20000000-0000-0000-0000-000000000001"),
        ),
        (
            UUID("10000000-0000-0000-0000-000000000001"),
            UUID("20000000-0000-0000-0000-000000000099"),
        ),
    ],
)
def test_get_success_returns_none_when_chapter_does_not_match(
    mysql_session: Session,
    lookup_textbook_id: UUID,
    lookup_chapter_id: UUID,
) -> None:
    """Chapterが指定Textbookに属さないか存在しない場合にNoneを返すことを確認する。"""
    textbook_id = UUID("10000000-0000-0000-0000-000000000001")
    chapter_id = UUID("20000000-0000-0000-0000-000000000001")
    _store_textbooks(mysql_session, textbook_id)
    mysql_session.add(
        ChapterTable(
            id=chapter_id,
            textbook_id=textbook_id,
            title="第1章",
            position=0,
            content="first",
            workspace_preset_key=None,
        )
    )
    mysql_session.commit()
    repository = SqlAlchemyChapterRepository(mysql_session)

    chapter = repository.get(lookup_textbook_id, lookup_chapter_id)

    assert chapter is None
