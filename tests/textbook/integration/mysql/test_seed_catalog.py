from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from scripts.seed_catalog import _generate_catalog, _seed_catalog, _SeedCatalogConflictError
from src.textbook.infra.database import (
    ChapterTable,
    SqlAlchemyChapterRepository,
    SqlAlchemyTextbookRepository,
    TextbookTable,
)


def _read_seeded_catalog(
    session: Session, textbook_ids: set[UUID]
) -> tuple[dict[UUID, str], dict[UUID, tuple[UUID, int, str, str, str | None]]]:
    """既存RepositoryからTextbookとChapterの値を読み取る。"""
    textbook_repository = SqlAlchemyTextbookRepository(session)
    chapter_repository = SqlAlchemyChapterRepository(session)
    textbooks = {textbook.id: textbook.title.value for textbook in textbook_repository.list()}
    chapters = {
        chapter.id: (
            chapter.textbook_id,
            chapter.position.value,
            chapter.title.value,
            chapter.content.value,
            chapter.workspace_preset_key,
        )
        for textbook_id in textbook_ids
        for chapter in chapter_repository.list(textbook_id)
    }
    return textbooks, chapters


@pytest.mark.integration
def test_seed_catalog_success_is_idempotent_and_preserves_non_seed_rows(mysql_session: Session) -> None:
    """同じCatalogを再投入しても対応が変わらず、生成対象外の行が維持されることを確認する。"""
    catalog = _generate_catalog(2, 2)
    non_seed_textbook_id = UUID("70000000-0000-0000-0000-000000000001")
    non_seed_chapter_id = UUID("70000000-0000-0000-0000-000000000002")
    mysql_session.add(TextbookTable(id=non_seed_textbook_id, title="Non-seed textbook"))
    mysql_session.flush()
    mysql_session.add(
        ChapterTable(
            id=non_seed_chapter_id,
            textbook_id=non_seed_textbook_id,
            title="Non-seed chapter",
            position=0,
            content="preserve me",
            workspace_preset_key="non-seed",
        )
    )
    mysql_session.commit()

    _seed_catalog(mysql_session, catalog)
    mysql_session.commit()
    all_textbook_ids = {textbook.id for textbook in catalog} | {non_seed_textbook_id}
    first_textbooks, first_chapters = _read_seeded_catalog(mysql_session, all_textbook_ids)
    mysql_session.commit()

    _seed_catalog(mysql_session, _generate_catalog(2, 2))
    mysql_session.commit()
    second_textbooks, second_chapters = _read_seeded_catalog(mysql_session, all_textbook_ids)

    expected_textbooks = {textbook.id: textbook.title for textbook in catalog}
    expected_textbooks[non_seed_textbook_id] = "Non-seed textbook"
    expected_chapters: dict[UUID, tuple[UUID, int, str, str, str | None]] = {
        chapter.id: (
            chapter.textbook_id,
            chapter.position,
            chapter.title,
            chapter.content,
            None,
        )
        for textbook in catalog
        for chapter in textbook.chapters
    }
    expected_chapters[non_seed_chapter_id] = (
        non_seed_textbook_id,
        0,
        "Non-seed chapter",
        "preserve me",
        "non-seed",
    )

    assert first_textbooks == expected_textbooks
    assert first_chapters == expected_chapters
    assert second_textbooks == first_textbooks
    assert second_chapters == first_chapters


@pytest.mark.integration
def test_seed_catalog_failure_rolls_back_when_chapter_position_is_occupied(mysql_session: Session) -> None:
    """Chapter位置の競合時に、Seed対象と既存行を変更せずrollbackすることを確認する。"""
    catalog = _generate_catalog(2, 1)
    conflict_chapter_id = UUID("70000000-0000-0000-0000-000000000003")
    mysql_session.add_all(
        [
            TextbookTable(id=catalog[0].id, title="Before seed"),
            TextbookTable(id=catalog[1].id, title=catalog[1].title),
        ]
    )
    mysql_session.flush()
    mysql_session.add(
        ChapterTable(
            id=conflict_chapter_id,
            textbook_id=catalog[1].id,
            title="Existing chapter",
            position=0,
            content="Keep this chapter",
            workspace_preset_key=None,
        )
    )
    mysql_session.commit()

    with pytest.raises(_SeedCatalogConflictError):
        with mysql_session.begin():
            _seed_catalog(mysql_session, catalog)

    textbook_repository = SqlAlchemyTextbookRepository(mysql_session)
    chapter_repository = SqlAlchemyChapterRepository(mysql_session)
    textbook = textbook_repository.get(catalog[0].id)
    chapters = chapter_repository.list(catalog[1].id)

    assert textbook is not None
    assert textbook.title.value == "Before seed"
    assert [(chapter.id, chapter.title.value, chapter.content.value) for chapter in chapters] == [
        (conflict_chapter_id, "Existing chapter", "Keep this chapter")
    ]
