from src.shared.application.ports import UnitOfWork
from src.textbook.application.models import ListTextbooksOutput, TextbookSummary
from src.textbook.application.ports import TextbookRepository


class ListTextbooks:
    """教科書の一覧を取得する。"""

    def __init__(self, textbook_repository: TextbookRepository, unit_of_work: UnitOfWork) -> None:
        self._textbook_repository = textbook_repository
        self._unit_of_work = unit_of_work

    def execute(self) -> ListTextbooksOutput:
        """すべての教科書を一覧表示用の形式で返す。"""
        with self._unit_of_work:
            textbooks = self._textbook_repository.list()

            return ListTextbooksOutput(
                textbooks=tuple(
                    TextbookSummary(
                        id=textbook.id,
                        title=textbook.title.value,
                    )
                    for textbook in textbooks
                )
            )
