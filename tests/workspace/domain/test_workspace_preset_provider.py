from uuid import UUID

import pytest

from src.workspace.domain import (
    WorkspaceComponent,
    WorkspaceDefinition,
    WorkspacePresetKey,
    WorkspacePresetProvider,
    create_system_workspace_preset_provider,
)

UBUNTU_PRESET_KEY = WorkspacePresetKey("ws-ubuntu-24_04")
UBUNTU_DEFINITION_ID = UUID("1f8d7e6c-1e1b-4a4f-8b49-3a57e08ab8a5")
OTHER_PRESET_KEY = WorkspacePresetKey("ws-other")
OTHER_DEFINITION_ID = UUID("266257e2-c874-46b9-9e98-0976b584d52f")


def _definition(definition_id: UUID) -> WorkspaceDefinition:
    return WorkspaceDefinition(
        definition_id=definition_id,
        components=(WorkspaceComponent(component_key="main", image="ubuntu:24.04"),),
    )


def test_create_system_workspace_preset_provider_success_creates_independent_instances() -> None:
    """Factory呼び出しごとに独立したWorkspacePresetProviderを生成できることを確認する。"""
    assert create_system_workspace_preset_provider() is not create_system_workspace_preset_provider()


def test_create_system_workspace_preset_provider_success_lists_available_preset_keys() -> None:
    """利用側がProviderからシステム提供Preset keyの一覧を取得できることを確認する。"""
    provider = create_system_workspace_preset_provider()

    assert provider.list_preset_keys() == (UBUNTU_PRESET_KEY,)


def test_create_system_workspace_preset_provider_success_resolves_ubuntu_definition() -> None:
    """Ubuntu 24.04のPreset keyから完成済みDefinitionを取得できることを確認する。"""
    provider = create_system_workspace_preset_provider()

    preset = provider.get(UBUNTU_PRESET_KEY)

    assert preset is not None
    assert preset.preset_key == UBUNTU_PRESET_KEY
    assert preset.definition.definition_id == UBUNTU_DEFINITION_ID
    assert len(preset.definition.components) == 1
    component = preset.definition.components[0]
    assert component.component_key == "main"
    assert component.image == "ubuntu:24.04"
    assert component.startup_command == ("sleep", "infinity")
    assert component.terminal_exec is not None
    assert component.terminal_exec.command == ("/bin/bash",)


def test_create_system_workspace_preset_provider_success_lists_completed_presets() -> None:
    """登録処理がProviderからシステム提供Presetを増減に依存せず全件取得できることを確認する。"""
    provider = create_system_workspace_preset_provider()

    presets = provider.list_presets()

    assert tuple(preset.preset_key for preset in presets) == provider.list_preset_keys()


def test_create_system_workspace_preset_provider_success_returns_none_for_unknown_key() -> None:
    """定義されていないPreset keyの取得結果がNoneになることを確認する。"""
    provider = create_system_workspace_preset_provider()

    assert provider.get(WorkspacePresetKey("unknown")) is None


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
