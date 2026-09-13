from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from src.workspace.domain import WorkspaceComponent, WorkspaceDefinition, WorkspacePreset, WorkspacePresetKey

WORKSPACE_PRESET_KEY = WorkspacePresetKey("ws-ubuntu-24_04")
WORKSPACE_DEFINITION = WorkspaceDefinition(
    definition_id=UUID("1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5"),
    components=(WorkspaceComponent(component_key="main", image="ubuntu:24.04"),),
)


def test_workspace_preset_success_exposes_key_and_definition() -> None:
    """WorkspacePresetからPreset keyと完成済みDefinitionを参照できることを確認する。"""
    preset = WorkspacePreset(preset_key=WORKSPACE_PRESET_KEY, definition=WORKSPACE_DEFINITION)

    assert preset.preset_key == WORKSPACE_PRESET_KEY
    assert preset.definition is WORKSPACE_DEFINITION


@pytest.mark.parametrize(
    ("preset_key", "definition"),
    [
        (object(), WORKSPACE_DEFINITION),
        (WORKSPACE_PRESET_KEY, object()),
    ],
)
def test_workspace_preset_failure_rejects_invalid_property_types(preset_key: object, definition: object) -> None:
    """WorkspacePresetへDomain Model以外の値を指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspacePreset(
            preset_key=preset_key,  # type: ignore[arg-type]
            definition=definition,  # type: ignore[arg-type]
        )


def test_workspace_preset_failure_rejects_property_assignment() -> None:
    """生成済みWorkspacePresetのKeyとDefinitionを変更できないことを確認する。"""
    preset = WorkspacePreset(preset_key=WORKSPACE_PRESET_KEY, definition=WORKSPACE_DEFINITION)

    with pytest.raises(FrozenInstanceError):
        preset.preset_key = WorkspacePresetKey("other")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        preset.definition = WORKSPACE_DEFINITION  # type: ignore[misc]


def test_workspace_preset_failure_rejects_positional_arguments() -> None:
    """WorkspacePresetのプロパティを位置引数で指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspacePreset(WORKSPACE_PRESET_KEY, WORKSPACE_DEFINITION)  # type: ignore[call-arg]
