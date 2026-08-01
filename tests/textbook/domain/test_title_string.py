from dataclasses import FrozenInstanceError

import pytest

from src.textbook.domain.entities import TitleString


def test_title_string_success_removes_surrounding_whitespace() -> None:
    """前後の空白を除去し、途中の空白と特殊文字を保持することを確認する。"""
    title = TitleString("\t Niora !@#$%^&*() の  教科書 \n")

    assert title.value == "Niora !@#$%^&*() の  教科書"


@pytest.mark.parametrize("value", ["a", "a" * 128])
def test_title_string_success_accepts_boundary_length(value: str) -> None:
    """1文字以上128文字以下のタイトルを生成できることを確認する。"""
    assert TitleString(value).value == value


@pytest.mark.parametrize("value", ["", " ", "\n\t"])
def test_title_string_failure_rejects_empty_title(value: str) -> None:
    """空または空白だけのタイトルを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        TitleString(value)


def test_title_string_failure_rejects_title_over_maximum_length() -> None:
    """128文字を超えるタイトルを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        TitleString("a" * 129)


def test_title_string_failure_rejects_non_string_value() -> None:
    """文字列以外からタイトルを生成できないことを確認する。"""
    with pytest.raises(TypeError):
        TitleString(object())  # type: ignore[arg-type]


def test_title_string_failure_rejects_value_assignment() -> None:
    """生成済みのタイトルを直接変更できないことを確認する。"""
    title = TitleString("タイトル")

    with pytest.raises(FrozenInstanceError):
        title.value = "変更後のタイトル"  # type: ignore[misc]
