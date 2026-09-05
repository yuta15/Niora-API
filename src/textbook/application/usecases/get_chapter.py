from src.shared.application.ports import UnitOfWork
from src.textbook.application.models import GetChapterInput, GetChapterOutput
from src.textbook.application.ports import ChapterRepository


class GetChapter:
    """指定された章の表示内容を取得する。"""

    def __init__(self, chapter_repository: ChapterRepository, unit_of_work: UnitOfWork) -> None:
        self._chapter_repository = chapter_repository
        self._unit_of_work = unit_of_work

    def execute(self, input: GetChapterInput) -> GetChapterOutput | None:
        """章を取得し、存在しない場合はNoneを返す。"""
        with self._unit_of_work:
            chapter = self._chapter_repository.get(input.textbook_id, input.chapter_id)
            if chapter is None:
                return None

            return GetChapterOutput(
                id=chapter.id,
                title=chapter.title.value,
                content=chapter.content.value,
                workspace_preset_key=chapter.workspace_preset_key,
            )
