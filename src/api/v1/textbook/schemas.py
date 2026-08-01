from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.textbook.application.models import GetChapterOutput, GetTextbookOutput, ListTextbooksOutput


class TextbookSummaryResponse(BaseModel):
    """教科書一覧に含める教科書の概要。"""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str


class ChapterSummaryResponse(BaseModel):
    """教科書詳細に含める章の概要。"""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    position: int


class ListTextbooksResponse(BaseModel):
    """教科書一覧のレスポンス。"""

    model_config = ConfigDict(frozen=True)

    textbooks: tuple[TextbookSummaryResponse, ...]

    @classmethod
    def from_output(cls, output: ListTextbooksOutput) -> ListTextbooksResponse:
        """Applicationの出力をAPIレスポンスへ変換する。"""
        return cls(
            textbooks=tuple(
                TextbookSummaryResponse(id=textbook.id, title=textbook.title) for textbook in output.textbooks
            )
        )


class GetTextbookResponse(BaseModel):
    """教科書詳細のレスポンス。"""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    chapters: tuple[ChapterSummaryResponse, ...]

    @classmethod
    def from_output(cls, output: GetTextbookOutput) -> GetTextbookResponse:
        """Applicationの出力をAPIレスポンスへ変換する。"""
        return cls(
            id=output.id,
            title=output.title,
            chapters=tuple(
                ChapterSummaryResponse(
                    id=chapter.id,
                    title=chapter.title,
                    position=chapter.position,
                )
                for chapter in output.chapters
            ),
        )


class GetChapterResponse(BaseModel):
    """章詳細のレスポンス。"""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str
    content: str

    @classmethod
    def from_output(cls, output: GetChapterOutput) -> GetChapterResponse:
        """Applicationの出力をAPIレスポンスへ変換する。"""
        return cls(id=output.id, title=output.title, content=output.content)
