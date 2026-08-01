from uuid import UUID

from .value_objects import TitleString


class Textbook:
    """教科書を表すエンティティ。"""

    def __init__(self, id: UUID, title: TitleString) -> None:
        if not isinstance(id, UUID):
            raise TypeError("textbook id must be a UUID")
        if not isinstance(title, TitleString):
            raise TypeError("textbook title must be a TitleString")

        self._id = id
        self._title = title

    @property
    def id(self) -> UUID:
        """教科書の識別子を返す。"""
        return self._id

    @property
    def title(self) -> TitleString:
        """教科書のタイトルを返す。"""
        return self._title

    def change_title(self, title: TitleString) -> None:
        """教科書のタイトルを変更する。"""
        if not isinstance(title, TitleString):
            raise TypeError("textbook title must be a TitleString")

        self._title = title
