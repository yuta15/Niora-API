from dataclasses import FrozenInstanceError

import pytest

from src.textbook.domain.entities import ContentString


@pytest.mark.parametrize("value", ["", "本文", "  前後の空白を含む本文  "])
def test_content_string_success_accepts_string(value: str) -> None:
    """空文字列や空白を含む文字列をそのまま本文にできることを確認する。"""
    assert ContentString(value).value == value


def test_content_string_failure_rejects_non_string_value() -> None:
    """文字列以外から本文を生成できないことを確認する。"""
    with pytest.raises(TypeError):
        ContentString(object())  # type: ignore[arg-type]


def test_content_string_failure_rejects_value_assignment() -> None:
    """生成済みの本文を直接変更できないことを確認する。"""
    content = ContentString("本文")

    with pytest.raises(FrozenInstanceError):
        content.value = "変更後の本文"  # type: ignore[misc]
