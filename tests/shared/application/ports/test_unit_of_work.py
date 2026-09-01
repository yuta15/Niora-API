import pytest

from src.shared.application.ports import UnitOfWork


class FakeUnitOfWork(UnitOfWork):
    """UnitOfWorkのTemplate Methodを検証するFake。"""

    def __init__(
        self,
        commit_error: BaseException | None = None,
        rollback_error: BaseException | None = None,
    ) -> None:
        self.events: list[str] = []
        self._commit_error = commit_error
        self._rollback_error = rollback_error

    def _commit(self) -> None:
        self.events.append("commit")
        if self._commit_error is not None:
            raise self._commit_error

    def _rollback(self) -> None:
        self.events.append("rollback")
        if self._rollback_error is not None:
            raise self._rollback_error


def test_context_manager_success_commits_automatically() -> None:
    """Context Managerを正常終了すると明示的なcommitなしでcommitすることを確認する。"""
    unit_of_work = FakeUnitOfWork()

    with unit_of_work:
        pass

    assert unit_of_work.events == ["commit"]


def test_context_manager_failure_rolls_back_and_propagates_original_exception() -> None:
    """処理中の例外でrollbackし、元の例外を抑制せず伝播することを確認する。"""
    unit_of_work = FakeUnitOfWork()
    expected_error = RuntimeError("use case failed")

    with pytest.raises(RuntimeError) as exception_info:
        with unit_of_work:
            raise expected_error

    assert exception_info.value is expected_error
    assert unit_of_work.events == ["rollback"]


def test_context_manager_commit_failure_rolls_back_and_propagates_commit_exception() -> None:
    """commit失敗時にrollbackし、commitの例外を伝播することを確認する。"""
    expected_error = RuntimeError("commit failed")
    unit_of_work = FakeUnitOfWork(commit_error=expected_error)

    with pytest.raises(RuntimeError) as exception_info:
        with unit_of_work:
            pass

    assert exception_info.value is expected_error
    assert unit_of_work.events == ["commit", "rollback"]


def test_context_manager_failure_preserves_original_exception_when_rollback_fails() -> None:
    """処理例外後のrollbackも失敗した場合に元の処理例外を送出し、rollback例外をcauseにすることを確認する。"""
    use_case_error = RuntimeError("use case failed")
    rollback_error = RuntimeError("rollback failed")
    unit_of_work = FakeUnitOfWork(rollback_error=rollback_error)

    with pytest.raises(RuntimeError) as exception_info:
        with unit_of_work:
            raise use_case_error

    assert exception_info.value is use_case_error
    assert exception_info.value.__cause__ is rollback_error
    assert unit_of_work.events == ["rollback"]


def test_context_manager_commit_failure_preserves_commit_exception_when_rollback_fails() -> None:
    """commit失敗後のrollbackも失敗した場合に元のcommit例外を送出し、rollback例外をcauseにすることを確認する。"""
    commit_error = RuntimeError("commit failed")
    rollback_error = RuntimeError("rollback failed")
    unit_of_work = FakeUnitOfWork(commit_error=commit_error, rollback_error=rollback_error)

    with pytest.raises(RuntimeError) as exception_info:
        with unit_of_work:
            pass

    assert exception_info.value is commit_error
    assert exception_info.value.__cause__ is rollback_error
    assert unit_of_work.events == ["commit", "rollback"]
