from dataclasses import FrozenInstanceError

import pytest

from src.textbook.domain.entities import ChapterPosition


@pytest.mark.parametrize("value", [1, 2])
def test_chapter_position_success_accepts_positive_integer(value: int) -> None:
    """1以上の整数を章の位置にできることを確認する。"""
    assert ChapterPosition(value).value == value


@pytest.mark.parametrize(
    ("value", "expected_exception"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        ("1", TypeError),
    ],
)
def test_chapter_position_failure_rejects_invalid_value(
    value: object,
    expected_exception: type[Exception],
) -> None:
    """0以下または整数以外を章の位置にできないことを確認する。"""
    with pytest.raises(expected_exception):
        ChapterPosition(value)  # type: ignore[arg-type]


def test_chapter_position_failure_rejects_value_assignment() -> None:
    """生成済みの章の位置を直接変更できないことを確認する。"""
    position = ChapterPosition(1)

    with pytest.raises(FrozenInstanceError):
        position.value = 2  # type: ignore[misc]
