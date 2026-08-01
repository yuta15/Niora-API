from uuid import UUID

import pytest

from src.textbook.domain.entities.textbook import Textbook
from src.textbook.domain.entities.value_objects import TitleString

TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
OTHER_TEXTBOOK_ID = UUID("38e3ae7b-357f-44ea-b0d8-f8499fc3f132")


@pytest.mark.parametrize("argument_name", ["id", "title"])
def test_init_failure_rejects_invalid_argument_type(argument_name: str) -> None:
    """教科書がUUIDとTitleString以外から生成されないことを確認する。"""
    arguments: dict[str, object] = {
        "id": TEXTBOOK_ID,
        "title": TitleString("教科書のタイトル"),
    }
    arguments[argument_name] = object()

    with pytest.raises(TypeError):
        Textbook(**arguments)  # type: ignore[arg-type]


def test_change_title_success_updates_only_title() -> None:
    """教科書のタイトルを変更しても識別子が維持されることを確認する。"""
    textbook = Textbook(id=TEXTBOOK_ID, title=TitleString("変更前のタイトル"))

    textbook.change_title(TitleString("変更後のタイトル"))

    assert textbook.title == TitleString("変更後のタイトル")
    assert textbook.id == TEXTBOOK_ID


def test_change_title_failure_rejects_invalid_type() -> None:
    """TitleString以外を指定した場合に教科書のタイトルが維持されることを確認する。"""
    textbook = Textbook(id=TEXTBOOK_ID, title=TitleString("変更前のタイトル"))

    with pytest.raises(TypeError):
        textbook.change_title(object())  # type: ignore[arg-type]

    assert textbook.title == TitleString("変更前のタイトル")


@pytest.mark.parametrize(
    ("attribute_name", "new_value"),
    [
        ("id", OTHER_TEXTBOOK_ID),
        ("title", TitleString("直接代入するタイトル")),
    ],
)
def test_property_assignment_failure_is_rejected(attribute_name: str, new_value: object) -> None:
    """教科書の公開プロパティを直接変更できないことを確認する。"""
    textbook = Textbook(id=TEXTBOOK_ID, title=TitleString("教科書のタイトル"))

    with pytest.raises(AttributeError):
        setattr(textbook, attribute_name, new_value)
