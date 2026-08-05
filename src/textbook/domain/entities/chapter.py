from uuid import UUID

from .value_objects import ChapterPosition, ContentString, TitleString


class Chapter:
    """教科書を構成し、必要に応じて学習環境と対応する章。"""

    def __init__(
        self,
        id: UUID,
        textbook_id: UUID,
        position: ChapterPosition,
        title: TitleString,
        content: ContentString,
        workspace_preset_key: str | None = None,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("chapter id must be a UUID")
        if not isinstance(textbook_id, UUID):
            raise TypeError("textbook id must be a UUID")
        if not isinstance(position, ChapterPosition):
            raise TypeError("chapter position must be a ChapterPosition")
        if not isinstance(title, TitleString):
            raise TypeError("chapter title must be a TitleString")
        if not isinstance(content, ContentString):
            raise TypeError("chapter content must be a ContentString")
        if workspace_preset_key is not None and not isinstance(workspace_preset_key, str):
            raise TypeError("workspace preset key must be a string or None")
        if workspace_preset_key == "":
            raise ValueError("workspace preset key must not be empty")

        self._id = id
        self._textbook_id = textbook_id
        self._position = position
        self._title = title
        self._content = content
        self._workspace_preset_key = workspace_preset_key

    @property
    def id(self) -> UUID:
        """章の識別子を返す。"""
        return self._id

    @property
    def textbook_id(self) -> UUID:
        """章が属する教科書の識別子を返す。"""
        return self._textbook_id

    @property
    def position(self) -> ChapterPosition:
        """教科書内における章の位置を返す。"""
        return self._position

    @property
    def title(self) -> TitleString:
        """章のタイトルを返す。"""
        return self._title

    @property
    def content(self) -> ContentString:
        """章の本文を返す。"""
        return self._content

    @property
    def workspace_preset_key(self) -> str | None:
        """章に紐づくWorkspacePresetKeyを返す。"""
        return self._workspace_preset_key

    def change_title(self, title: TitleString) -> None:
        """章のタイトルを変更する。"""
        if not isinstance(title, TitleString):
            raise TypeError("chapter title must be a TitleString")

        self._title = title

    def change_content(self, content: ContentString) -> None:
        """章の本文を変更する。"""
        if not isinstance(content, ContentString):
            raise TypeError("chapter content must be a ContentString")

        self._content = content

    def change_position(self, position: ChapterPosition) -> None:
        """教科書内における章の位置を変更する。"""
        if not isinstance(position, ChapterPosition):
            raise TypeError("chapter position must be a ChapterPosition")

        self._position = position

    def change_workspace_preset_key(self, workspace_preset_key: str | None) -> None:
        """章に紐づくWorkspacePresetKeyを変更する。"""
        if workspace_preset_key is not None and not isinstance(workspace_preset_key, str):
            raise TypeError("workspace preset key must be a string or None")
        if workspace_preset_key == "":
            raise ValueError("workspace preset key must not be empty")

        self._workspace_preset_key = workspace_preset_key
