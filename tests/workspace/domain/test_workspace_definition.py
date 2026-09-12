from uuid import UUID

import pytest

from src.workspace.domain.entities import WorkspaceComponent, WorkspaceDefinition

WORKSPACE_DEFINITION_ID = UUID("abf16f80-9172-4f28-927f-e8fe5b3fcd2a")
OTHER_WORKSPACE_DEFINITION_ID = UUID("44c5a5bd-3358-4b32-bf04-93b0bb969cd9")


def _workspace_component(component_key: str = "ubuntu") -> WorkspaceComponent:
    return WorkspaceComponent(component_key=component_key, image="ubuntu:latest")


def test_workspace_definition_success_exposes_properties() -> None:
    """WorkspaceDefinitionの識別子とComponent列を参照できることを確認する。"""
    components = (_workspace_component(),)
    definition = WorkspaceDefinition(
        definition_id=WORKSPACE_DEFINITION_ID,
        components=components,
    )

    assert definition.definition_id == WORKSPACE_DEFINITION_ID
    assert definition.components == components


def test_workspace_definition_failure_rejects_non_uuid_definition_id() -> None:
    """UUID以外をWorkspaceDefinitionの識別子に指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceDefinition(
            definition_id="not-a-uuid",  # type: ignore[arg-type]
            components=(_workspace_component(),),
        )


def test_workspace_definition_failure_rejects_empty_components() -> None:
    """Componentを持たないWorkspaceDefinitionを生成できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspaceDefinition(definition_id=WORKSPACE_DEFINITION_ID, components=())


def test_workspace_definition_failure_rejects_non_workspace_component() -> None:
    """WorkspaceComponent以外の値をDefinitionのComponentに指定できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceDefinition(
            definition_id=WORKSPACE_DEFINITION_ID,
            components=(object(),),  # type: ignore[arg-type]
        )


def test_workspace_definition_failure_rejects_duplicate_component_keys() -> None:
    """Definition内で重複するComponent keyを指定できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspaceDefinition(
            definition_id=WORKSPACE_DEFINITION_ID,
            components=(_workspace_component(), _workspace_component()),
        )


def test_workspace_definition_failure_rejects_property_assignment() -> None:
    """生成済みのWorkspaceDefinitionの公開プロパティを変更できないことを確認する。"""
    definition = WorkspaceDefinition(
        definition_id=WORKSPACE_DEFINITION_ID,
        components=(_workspace_component(),),
    )

    with pytest.raises(AttributeError):
        definition.definition_id = OTHER_WORKSPACE_DEFINITION_ID  # type: ignore[misc]

    with pytest.raises(AttributeError):
        definition.components = (_workspace_component("database"),)  # type: ignore[misc]


def test_workspace_definition_failure_rejects_positional_arguments() -> None:
    """WorkspaceDefinitionを位置引数で生成できないことを確認する。"""
    with pytest.raises(TypeError):
        WorkspaceDefinition(WORKSPACE_DEFINITION_ID, (_workspace_component(),))  # type: ignore[call-arg]
