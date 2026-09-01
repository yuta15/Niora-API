import pytest
from sqlalchemy import Table

from src.textbook.infra.database import ChapterTable, TextbookTable


@pytest.mark.parametrize(
    ("table", "expected_constraint_names"),
    [
        (TextbookTable.__table__, {"ck_textbook_title_not_empty", "pk_textbook"}),
        (
            ChapterTable.__table__,
            {
                "ck_chapter_position_non_negative",
                "ck_chapter_title_not_empty",
                "fk_chapter_textbook_id_textbook",
                "pk_chapter",
                "uq_chapter_textbook_id_position",
            },
        ),
    ],
)
def test_table_constraints_success_have_stable_names(
    table: Table,
    expected_constraint_names: set[str],
) -> None:
    """Table Modelの制約名がMigrationで参照できる安定した名前になることを確認する。"""
    assert {constraint.name for constraint in table.constraints} == expected_constraint_names
