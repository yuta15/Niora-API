from uuid import UUID

import pytest

from src.textbook.domain.entities import Chapter, ChapterPosition, ContentString, TitleString

CHAPTER_ID = UUID("35e2a8e4-b60c-412a-9406-ce999b15fcd3")
OTHER_CHAPTER_ID = UUID("8498bf44-f8f8-42e8-bdb6-5f60b2b51b7c")
TEXTBOOK_ID = UUID("d9e259cb-c537-451b-b38b-90443f553185")
OTHER_TEXTBOOK_ID = UUID("38e3ae7b-357f-44ea-b0d8-f8499fc3f132")
WORKSPACE_PRESET_KEY = "ws-ubuntu-24_04"
OTHER_WORKSPACE_PRESET_KEY = "ws-ubuntu-26_04"


def _chapter(workspace_preset_key: str | None = WORKSPACE_PRESET_KEY) -> Chapter:
    return Chapter(
        id=CHAPTER_ID,
        textbook_id=TEXTBOOK_ID,
        position=ChapterPosition(1),
        title=TitleString("変更前のタイトル"),
        content=ContentString("変更前の本文"),
        workspace_preset_key=workspace_preset_key,
    )


@pytest.mark.parametrize(
    "argument_name",
    ["id", "textbook_id", "position", "title", "content", "workspace_preset_key"],
)
def test_init_failure_rejects_invalid_argument_type(argument_name: str) -> None:
    """章がUUIDと所定の値オブジェクト以外から生成されないことを確認する。"""
    arguments: dict[str, object] = {
        "id": CHAPTER_ID,
        "textbook_id": TEXTBOOK_ID,
        "position": ChapterPosition(1),
        "title": TitleString("章のタイトル"),
        "content": ContentString("章の本文"),
        "workspace_preset_key": WORKSPACE_PRESET_KEY,
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
    assert chapter.workspace_preset_key == WORKSPACE_PRESET_KEY


def test_change_content_success_accepts_empty_content() -> None:
    """章の本文を空文字列へ変更してもほかの状態が維持されることを確認する。"""
    chapter = _chapter()

    chapter.change_content(ContentString(""))

    assert chapter.content == ContentString("")
    assert chapter.id == CHAPTER_ID
    assert chapter.textbook_id == TEXTBOOK_ID
    assert chapter.position == ChapterPosition(1)
    assert chapter.title == TitleString("変更前のタイトル")
    assert chapter.workspace_preset_key == WORKSPACE_PRESET_KEY


def test_change_position_success_updates_only_position() -> None:
    """教科書内の章の位置を変更してもほかの状態が維持されることを確認する。"""
    chapter = _chapter()

    chapter.change_position(ChapterPosition(2))

    assert chapter.position == ChapterPosition(2)
    assert chapter.id == CHAPTER_ID
    assert chapter.textbook_id == TEXTBOOK_ID
    assert chapter.title == TitleString("変更前のタイトル")
    assert chapter.content == ContentString("変更前の本文")
    assert chapter.workspace_preset_key == WORKSPACE_PRESET_KEY


def test_change_workspace_preset_key_success_associates_preset() -> None:
    """WorkspacePresetKeyが未設定の章へ新しく紐付けられることを確認する。"""
    chapter = _chapter(workspace_preset_key=None)

    chapter.change_workspace_preset_key(WORKSPACE_PRESET_KEY)

    assert chapter.workspace_preset_key == WORKSPACE_PRESET_KEY


def test_change_workspace_preset_key_success_replaces_preset() -> None:
    """章に紐づくWorkspacePresetKeyを別のキーへ変更できることを確認する。"""
    chapter = _chapter()

    chapter.change_workspace_preset_key(OTHER_WORKSPACE_PRESET_KEY)

    assert chapter.workspace_preset_key == OTHER_WORKSPACE_PRESET_KEY


def test_change_workspace_preset_key_success_removes_preset() -> None:
    """章とWorkspacePresetKeyの紐付けを解除できることを確認する。"""
    chapter = _chapter()

    chapter.change_workspace_preset_key(None)

    assert chapter.workspace_preset_key is None


def test_init_failure_rejects_empty_workspace_preset_key() -> None:
    """空文字列をWorkspacePresetKeyとして章へ紐付けられないことを確認する。"""
    with pytest.raises(ValueError):
        _chapter(workspace_preset_key="")


def test_change_workspace_preset_key_failure_rejects_empty_key() -> None:
    """WorkspacePresetKeyを空文字列へ変更できないことを確認する。"""
    chapter = _chapter()

    with pytest.raises(ValueError):
        chapter.change_workspace_preset_key("")

    assert chapter.workspace_preset_key == WORKSPACE_PRESET_KEY


@pytest.mark.parametrize(
    "method_name",
    [
        "change_title",
        "change_content",
        "change_position",
        "change_workspace_preset_key",
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
        chapter.workspace_preset_key,
    )

    with pytest.raises(TypeError):
        change(object())

    assert (
        chapter.id,
        chapter.textbook_id,
        chapter.position,
        chapter.title,
        chapter.content,
        chapter.workspace_preset_key,
    ) == original_state


@pytest.mark.parametrize(
    ("attribute_name", "new_value"),
    [
        ("id", OTHER_CHAPTER_ID),
        ("textbook_id", OTHER_TEXTBOOK_ID),
        ("position", ChapterPosition(2)),
        ("title", TitleString("直接代入するタイトル")),
        ("content", ContentString("直接代入する本文")),
        ("workspace_preset_key", OTHER_WORKSPACE_PRESET_KEY),
    ],
)
def test_property_assignment_failure_is_rejected(attribute_name: str, new_value: object) -> None:
    """章の公開プロパティを直接変更できないことを確認する。"""
    chapter = _chapter()

    with pytest.raises(AttributeError):
        setattr(chapter, attribute_name, new_value)
