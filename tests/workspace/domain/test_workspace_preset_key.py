from dataclasses import FrozenInstanceError

import pytest

from src.workspace.domain.entities import WorkspacePresetKey


@pytest.mark.parametrize("value", ["a", "a" * 128])
def test_workspace_preset_key_success_accepts_boundary_length(value: str) -> None:
    """1文字以上128文字以下のプリセットキーを生成できることを確認する。"""
    assert WorkspacePresetKey(value).value == value


@pytest.mark.parametrize("value", ["ws-ubuntu-24_04", "Ubuntu_24-04", "123"])
def test_workspace_preset_key_success_accepts_supported_characters(value: str) -> None:
    """ASCII英数字、ハイフン、アンダースコアをプリセットキーに使用できることを確認する。"""
    assert WorkspacePresetKey(value).value == value


@pytest.mark.parametrize("value", ["", "a" * 129])
def test_workspace_preset_key_failure_rejects_invalid_length(value: str) -> None:
    """空文字列または128文字を超えるプリセットキーを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetKey(value)


@pytest.mark.parametrize("value", ["ws ubuntu", "ws/ubuntu", "Ubuntu.24", "日本語"])
def test_workspace_preset_key_failure_rejects_unsupported_characters(value: str) -> None:
    """許可していない文字を含むプリセットキーを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetKey(value)


def test_workspace_preset_key_failure_rejects_non_string_value() -> None:
    """文字列以外からプリセットキーを生成できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspacePresetKey(object())  # type: ignore[arg-type]


def test_workspace_preset_key_failure_rejects_value_assignment() -> None:
    """生成済みのプリセットキーを直接変更できないことを確認する。"""
    preset_key = WorkspacePresetKey("ws-ubuntu-24_04")

    with pytest.raises(FrozenInstanceError):
        preset_key.value = "ws-ubuntu-26_04"  # type: ignore[misc]
