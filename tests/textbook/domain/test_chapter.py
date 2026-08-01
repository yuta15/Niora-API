from uuid import UUID

import pytest

from src.textbook.domain.entities.chapter import Chapter
from src.textbook.domain.entities.value_objects import ChapterPosition, ContentString, TitleString

CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
OTHER_CHAPTER_ID = UUID("8498bf44-f8f8-42e8-bdb6-5f60b2b51b7c")
TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
OTHER_TEXTBOOK_ID = UUID("38e3ae7b-357f-44ea-b0d8-f8499fc3f132")
WORKSPACE_DEFINITION_ID = UUID("2698ea2e-e0c9-4722-8eb6-f14659680306")
OTHER_WORKSPACE_DEFINITION_ID = UUID("8043bd5f-c87a-4192-8c72-73b5ff260722")


def _chapter(workspace_definition_id: UUID | None = WORKSPACE_DEFINITION_ID) -> Chapter:
    return Chapter(
        id=CHAPTER_ID,
        textbook_id=TEXTBOOK_ID,
        position=ChapterPosition(1),
        title=TitleString("変更前のタイトル"),
        content=ContentString("変更前の本文"),
        workspace_definition_id=workspace_definition_id,
    )


@pytest.mark.parametrize(
    "argument_name",
    ["id", "textbook_id", "position", "title", "content", "workspace_definition_id"],
)
def test_init_failure_rejects_invalid_argument_type(argument_name: str) -> None:
    """章がUUIDと所定の値オブジェクト以外から生成されないことを確認する。"""
    arguments: dict[str, object] = {
        "id": CHAPTER_ID,
        "textbook_id": TEXTBOOK_ID,
        "position": ChapterPosition(1),
        "title": TitleString("章のタイトル"),
        "content": ContentString("章の本文"),
        "workspace_definition_id": WORKSPACE_DEFINITION_ID,
    }
    arguments[argument_name] = object()

    with pytest.raises(TypeError):
        Chapter(**arguments)  # type: ignore[arg-type]


def test_change_title_success_updates_only_title() -> None:
    """章のタイトルを変更してもほかの状態が維持されることを確認する。"""
    chapter = _chapter()

    chapter.change_title(TitleString("変更後のタイトル"))

    assert chapter.title == TitleString("変更後のタイトル")
    assert chapter.id == CHAPTER_ID
    assert chapter.textbook_id == TEXTBOOK_ID
    assert chapter.position == ChapterPosition(1)
    assert chapter.content == ContentString("変更前の本文")
    assert chapter.workspace_definition_id == WORKSPACE_DEFINITION_ID


def test_change_content_success_accepts_empty_content() -> None:
    """章の本文を空文字列へ変更してもほかの状態が維持されることを確認する。"""
    chapter = _chapter()

    chapter.change_content(ContentString(""))

    assert chapter.content == ContentString("")
    assert chapter.id == CHAPTER_ID
    assert chapter.textbook_id == TEXTBOOK_ID
    assert chapter.position == ChapterPosition(1)
    assert chapter.title == TitleString("変更前のタイトル")
    assert chapter.workspace_definition_id == WORKSPACE_DEFINITION_ID


def test_change_position_success_updates_only_position() -> None:
    """教科書内の章の位置を変更してもほかの状態が維持されることを確認する。"""
    chapter = _chapter()

    chapter.change_position(ChapterPosition(2))

    assert chapter.position == ChapterPosition(2)
    assert chapter.id == CHAPTER_ID
    assert chapter.textbook_id == TEXTBOOK_ID
    assert chapter.title == TitleString("変更前のタイトル")
    assert chapter.content == ContentString("変更前の本文")
    assert chapter.workspace_definition_id == WORKSPACE_DEFINITION_ID


def test_change_workspace_definition_success_associates_definition() -> None:
    """WorkspaceDefinitionが未設定の章へ新しく紐付けられることを確認する。"""
    chapter = _chapter(workspace_definition_id=None)

    chapter.change_workspace_definition(WORKSPACE_DEFINITION_ID)

    assert chapter.workspace_definition_id == WORKSPACE_DEFINITION_ID


def test_change_workspace_definition_success_replaces_definition() -> None:
    """章に紐づくWorkspaceDefinitionを別の定義へ変更できることを確認する。"""
    chapter = _chapter()

    chapter.change_workspace_definition(OTHER_WORKSPACE_DEFINITION_ID)

    assert chapter.workspace_definition_id == OTHER_WORKSPACE_DEFINITION_ID


def test_change_workspace_definition_success_removes_definition() -> None:
    """章とWorkspaceDefinitionの紐付けを解除できることを確認する。"""
    chapter = _chapter()

    chapter.change_workspace_definition(None)

    assert chapter.workspace_definition_id is None


@pytest.mark.parametrize(
    "method_name",
    [
        "change_title",
        "change_content",
        "change_position",
        "change_workspace_definition",
    ],
)
def test_change_failure_rejects_invalid_type(method_name: str) -> None:
    """所定の型以外を指定した場合に章の状態が維持されることを確認する。"""
    chapter = _chapter()
    change = getattr(chapter, method_name)
    original_state = (
        chapter.id,
        chapter.textbook_id,
        chapter.position,
        chapter.title,
        chapter.content,
        chapter.workspace_definition_id,
    )

    with pytest.raises(TypeError):
        change(object())

    assert (
        chapter.id,
        chapter.textbook_id,
        chapter.position,
        chapter.title,
        chapter.content,
        chapter.workspace_definition_id,
    ) == original_state


@pytest.mark.parametrize(
    ("attribute_name", "new_value"),
    [
        ("id", OTHER_CHAPTER_ID),
        ("textbook_id", OTHER_TEXTBOOK_ID),
        ("position", ChapterPosition(2)),
        ("title", TitleString("直接代入するタイトル")),
        ("content", ContentString("直接代入する本文")),
        ("workspace_definition_id", OTHER_WORKSPACE_DEFINITION_ID),
    ],
)
def test_property_assignment_failure_is_rejected(attribute_name: str, new_value: object) -> None:
    """章の公開プロパティを直接変更できないことを確認する。"""
    chapter = _chapter()

    with pytest.raises(AttributeError):
        setattr(chapter, attribute_name, new_value)
