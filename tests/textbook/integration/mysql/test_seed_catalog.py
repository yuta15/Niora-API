from dataclasses import replace
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from scripts.seed_catalog import _generate_catalog, _seed_catalog
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
def test_seed_catalog_failure_rolls_back_writes_when_chapter_flush_fails(mysql_session: Session) -> None:
    """Textbook更新後のChapter書込み失敗時に、別接続から部分更新が見えないことを確認する。"""
    catalog = _generate_catalog(1, 2)
    textbook = catalog[0]
    catalog_with_duplicate_positions = (
        replace(
            textbook,
            chapters=(
                textbook.chapters[0],
                replace(textbook.chapters[1], position=textbook.chapters[0].position),
            ),
        ),
    )
    mysql_session.add(TextbookTable(id=textbook.id, title="Before seed"))
    mysql_session.commit()

    with pytest.raises(IntegrityError):
        with mysql_session.begin():
            _seed_catalog(mysql_session, catalog_with_duplicate_positions)

    engine = cast(Engine, mysql_session.get_bind())
    mysql_session.connection()
    with engine.connect() as verification_connection, Session(bind=verification_connection) as verification_session:
        textbook_repository = SqlAlchemyTextbookRepository(verification_session)
        chapter_repository = SqlAlchemyChapterRepository(verification_session)
        persisted_textbook = textbook_repository.get(textbook.id)
        persisted_chapters = chapter_repository.list(textbook.id)

    assert persisted_textbook is not None
    assert persisted_textbook.title.value == "Before seed"
    assert persisted_chapters == []
