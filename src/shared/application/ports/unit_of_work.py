from abc import ABC, abstractmethod
from types import TracebackType
from typing import Literal, Self


class UnitOfWork(ABC):
    """UseCase単位のTransactionをContext Managerとして管理する。"""

    def __enter__(self) -> Self:
        """Transaction境界へ入り、自身を返す。"""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        """正常終了時にcommitし、例外時にrollbackして例外を伝播させる。"""
        if exc_value is not None:
            self._rollback_preserving_exception(exc_value, traceback)
            return False

        try:
            self._commit()
        except BaseException as commit_error:
            self._rollback_preserving_exception(commit_error, commit_error.__traceback__)
            raise

        return False

    def _rollback_preserving_exception(
        self,
        original_error: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        """Rollback失敗時も元の例外を保持し、例外を抑制しない。"""
        try:
            self._rollback()
        except BaseException as rollback_error:
            raise original_error.with_traceback(traceback) from rollback_error

    @abstractmethod
    def _commit(self) -> None:
        """Transactionをcommitする。"""

    @abstractmethod
    def _rollback(self) -> None:
        """Transactionをrollbackする。"""
