from src.textbook.application.models import ChapterSummary, GetTextbookInput, GetTextbookOutput
from src.textbook.application.ports import ChapterRepository, TextbookRepository


class GetTextbook:
    """教科書と、その教科書に属する章の一覧を取得する。"""

    def __init__(
        self,
        textbook_repository: TextbookRepository,
        chapter_repository: ChapterRepository,
    ) -> None:
        self._textbook_repository = textbook_repository
        self._chapter_repository = chapter_repository

    def execute(self, input: GetTextbookInput) -> GetTextbookOutput | None:
        """指定された教科書を取得し、存在しない場合はNoneを返す。"""
        textbook = self._textbook_repository.get(input.textbook_id)
        if textbook is None:
            return None

        chapters = self._chapter_repository.list(input.textbook_id)

        return GetTextbookOutput(
            id=textbook.id,
            title=textbook.title.value,
            chapters=tuple(
                ChapterSummary(
                    id=chapter.id,
                    title=chapter.title.value,
                    position=chapter.position.value,
                )
                for chapter in chapters
            ),
        )
