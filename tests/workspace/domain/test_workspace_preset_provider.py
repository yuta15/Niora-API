from uuid import UUID

import pytest

from src.workspace.domain import WorkspaceComponent, WorkspaceDefinition, WorkspacePresetKey, WorkspacePresetProvider

UBUNTU_PRESET_KEY = WorkspacePresetKey("ws-ubuntu-24_04")
UBUNTU_DEFINITION_ID = UUID("1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")
OTHER_PRESET_KEY = WorkspacePresetKey("ws-other")
OTHER_DEFINITION_ID = UUID("266257e2-c874-46b9-9e98-0976b584d52f")


def _definition(definition_id: UUID) -> WorkspaceDefinition:
    return WorkspaceDefinition(
        definition_id=definition_id,
        components=(WorkspaceComponent(component_key="main", image="ubuntu:24.04"),),
    )


def test_workspace_preset_provider_failure_rejects_unassociated_preset_key() -> None:
    """Preset keyとDefinitionの対応が欠落したCatalogを利用できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetProvider(
            preset_keys=(UBUNTU_PRESET_KEY,),
            definitions=(_definition(UBUNTU_DEFINITION_ID),),
            definition_ids_by_preset_key={},
        )


def test_workspace_preset_provider_failure_rejects_unassociated_definition() -> None:
    """Preset keyから参照されないDefinitionを含むCatalogを利用できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetProvider(
            preset_keys=(UBUNTU_PRESET_KEY,),
            definitions=(_definition(UBUNTU_DEFINITION_ID),),
            definition_ids_by_preset_key={
                UBUNTU_PRESET_KEY: OTHER_DEFINITION_ID,
            },
        )


def test_workspace_preset_provider_failure_rejects_duplicate_preset_keys() -> None:
    """重複するPreset keyを含むCatalogを利用できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetProvider(
            preset_keys=(UBUNTU_PRESET_KEY, UBUNTU_PRESET_KEY),
            definitions=(_definition(UBUNTU_DEFINITION_ID),),
            definition_ids_by_preset_key={UBUNTU_PRESET_KEY: UBUNTU_DEFINITION_ID},
        )


def test_workspace_preset_provider_failure_rejects_duplicate_definition_ids() -> None:
    """重複するDefinition IDを含むCatalogを利用できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetProvider(
            preset_keys=(UBUNTU_PRESET_KEY,),
            definitions=(_definition(UBUNTU_DEFINITION_ID), _definition(UBUNTU_DEFINITION_ID)),
            definition_ids_by_preset_key={UBUNTU_PRESET_KEY: UBUNTU_DEFINITION_ID},
        )


def test_workspace_preset_provider_failure_rejects_shared_definition() -> None:
    """複数のPreset keyから同じDefinitionを参照できないことを確認する。"""
    with pytest.raises(ValueError):
        WorkspacePresetProvider(
            preset_keys=(UBUNTU_PRESET_KEY, OTHER_PRESET_KEY),
            definitions=(_definition(UBUNTU_DEFINITION_ID),),
            definition_ids_by_preset_key={
                UBUNTU_PRESET_KEY: UBUNTU_DEFINITION_ID,
                OTHER_PRESET_KEY: UBUNTU_DEFINITION_ID,
            },
        )
