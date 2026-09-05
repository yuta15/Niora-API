"""開発・検証用のTextbookとChapterをMySQLへ投入する。"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from uuid import UUID, uuid5

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.shared.infra.database import create_engine, create_session_factory
from src.shared.infra.settings import ApplicationDatabaseSettings
from src.textbook.infra.database import ChapterTable, TextbookTable

_SEED_NAMESPACE = UUID("8c6f9d25-3c8d-5a6e-9f1b-4e6d7a8c9b0d")
_MAX_TOTAL_CHAPTERS = 10


@dataclass(frozen=True, slots=True)
class _SeedChapter:
    """投入対象となるChapterの決定的な値。"""

    id: UUID
    textbook_id: UUID
    title: str
    position: int
    content: str


@dataclass(frozen=True, slots=True)
class _SeedTextbook:
    """投入対象となるTextbookとChapterの決定的な値。"""

    id: UUID
    title: str
    chapters: tuple[_SeedChapter, ...]


class _SeedCatalogConflictError(RuntimeError):
    """投入対象のChapter位置を別のChapterが占有している。"""


def _seed_id(name: str) -> UUID:
    """固定Namespaceと名前から投入対象のUUIDを生成する。"""
    return uuid5(_SEED_NAMESPACE, name)


def _generate_catalog(textbook_count: int, chapters_per_textbook: int) -> tuple[_SeedTextbook, ...]:
    """指定数の決定的な開発用Catalogを生成する。"""
    if textbook_count < 0:
        raise ValueError("textbook_count must be non-negative")
    if chapters_per_textbook < 0:
        raise ValueError("chapters_per_textbook must be non-negative")
    if textbook_count * chapters_per_textbook > _MAX_TOTAL_CHAPTERS:
        raise ValueError(f"total chapter count must be {_MAX_TOTAL_CHAPTERS} or fewer")

    textbooks: list[_SeedTextbook] = []
    for textbook_position in range(textbook_count):
        textbook_id = _seed_id(f"textbook:{textbook_position}")
        textbook_number = textbook_position + 1
        chapters = tuple(
            _SeedChapter(
                id=_seed_id(f"chapter:{textbook_position}:{chapter_position}"),
                textbook_id=textbook_id,
                title=f"Chapter {chapter_position + 1}",
                position=chapter_position,
                content=f"Generated content for Development Textbook {textbook_number}, Chapter {chapter_position + 1}.",
            )
            for chapter_position in range(chapters_per_textbook)
        )
        textbooks.append(
            _SeedTextbook(
                id=textbook_id,
                title=f"Development Textbook {textbook_number}",
                chapters=chapters,
            )
        )
    return tuple(textbooks)


def _seed_catalog(session: Session, catalog: tuple[_SeedTextbook, ...]) -> None:
    """Catalogを1つの呼び出し元Transactionへ投入し、既存の生成行を更新する。

    生成対象外の行は変更せず、対象位置の競合は変更前に検出して失敗する。
    Transactionの開始・commit・rollbackは呼び出し元が担当する。
    """
    if not catalog:
        return

    textbook_ids = [textbook.id for textbook in catalog]
    chapters = [chapter for textbook in catalog for chapter in textbook.chapters]
    chapter_ids = [chapter.id for chapter in chapters]

    existing_textbooks = session.scalars(select(TextbookTable).where(TextbookTable.id.in_(textbook_ids))).all()
    existing_chapters = session.scalars(
        select(ChapterTable).where(
            or_(
                ChapterTable.textbook_id.in_(textbook_ids),
                ChapterTable.id.in_(chapter_ids),
            )
        )
    ).all()

    chapters_by_slot = {(chapter.textbook_id, chapter.position): chapter for chapter in existing_chapters}
    existing_chapters_by_id = {chapter.id: chapter for chapter in existing_chapters}
    for expected_chapter in chapters:
        occupant = chapters_by_slot.get((expected_chapter.textbook_id, expected_chapter.position))
        if occupant is not None and occupant.id != expected_chapter.id:
            raise _SeedCatalogConflictError(
                f"chapter position is occupied: textbook_id={expected_chapter.textbook_id}, "
                f"position={expected_chapter.position}"
            )

    textbooks_by_id = {textbook.id: textbook for textbook in existing_textbooks}
    for expected_textbook in catalog:
        textbook = textbooks_by_id.get(expected_textbook.id)
        if textbook is None:
            session.add(TextbookTable(id=expected_textbook.id, title=expected_textbook.title))
        else:
            textbook.title = expected_textbook.title
    session.flush()

    for expected_chapter in chapters:
        chapter = existing_chapters_by_id.get(expected_chapter.id)
        if chapter is not None:
            chapter.textbook_id = expected_chapter.textbook_id
            chapter.title = expected_chapter.title
            chapter.position = expected_chapter.position
            chapter.content = expected_chapter.content
            chapter.workspace_preset_key = None
        else:
            session.add(
                ChapterTable(
                    id=expected_chapter.id,
                    textbook_id=expected_chapter.textbook_id,
                    title=expected_chapter.title,
                    position=expected_chapter.position,
                    content=expected_chapter.content,
                    workspace_preset_key=None,
                )
            )
    session.flush()


def _non_negative_int(value: str) -> int:
    """argparse用に非負整数を検証する。"""
    try:
        parsed = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an integer") from error
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _create_parser() -> argparse.ArgumentParser:
    """seed_catalog CLIのParserを生成する。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--textbooks",
        "--textbook-count",
        dest="textbook_count",
        required=True,
        type=_non_negative_int,
        help="生成するTextbook数",
    )
    parser.add_argument(
        "--chapters-per-textbook",
        "--chapter-count",
        dest="chapters_per_textbook",
        required=True,
        type=_non_negative_int,
        help="Textbookごとに生成するChapter数",
    )
    return parser


def _run(textbook_count: int, chapters_per_textbook: int) -> None:
    """Application用DatabaseへCatalogを単一Transactionで投入する。"""
    catalog = _generate_catalog(textbook_count, chapters_per_textbook)
    settings = ApplicationDatabaseSettings()  # type: ignore[call-arg]  # pyright: ignore[reportCallIssue]
    engine = create_engine(settings)
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session, session.begin():
            _seed_catalog(session, catalog)
    finally:
        engine.dispose()


def _main(argv: list[str] | None = None) -> int:
    """CLIを実行し、終了Codeを返す。"""
    parser = _create_parser()
    arguments = parser.parse_args(argv)
    if arguments.textbook_count * arguments.chapters_per_textbook > _MAX_TOTAL_CHAPTERS:
        parser.error(f"total chapter count must be {_MAX_TOTAL_CHAPTERS} or fewer")
    try:
        _run(arguments.textbook_count, arguments.chapters_per_textbook)
    except Exception as error:
        print(f"seed_catalog failed: {type(error).__name__}", file=sys.stderr)
        return 1

    print(f"Seeded {arguments.textbook_count} textbook(s) with {arguments.chapters_per_textbook} chapter(s) each.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
