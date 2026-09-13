from types import MappingProxyType

from ..entities.preset.definitions import SYSTEM_WORKSPACE_DEFINITIONS, UBUNTU_24_04_WORKSPACE_DEFINITION
from ..entities.preset.keys import SYSTEM_WORKSPACE_PRESET_KEYS, UBUNTU_24_04_WORKSPACE_PRESET_KEY
from .workspace_preset_provider import WorkspacePresetProvider

SYSTEM_WORKSPACE_PRESET_DEFINITION_IDS = MappingProxyType(
    {
        UBUNTU_24_04_WORKSPACE_PRESET_KEY: UBUNTU_24_04_WORKSPACE_DEFINITION.definition_id,
    }
)


def create_system_workspace_preset_provider() -> WorkspacePresetProvider:
    """システム提供Catalogを使用するWorkspacePresetProviderを生成する。"""
    return WorkspacePresetProvider(
        preset_keys=SYSTEM_WORKSPACE_PRESET_KEYS,
        definitions=SYSTEM_WORKSPACE_DEFINITIONS,
        definition_ids_by_preset_key=SYSTEM_WORKSPACE_PRESET_DEFINITION_IDS,
    )
